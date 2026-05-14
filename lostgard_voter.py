"""
Orchestrateur lostgard.fr — boucle infinie.
- Maintient la session Cloudflare active (curl_cffi / impersonate chrome110)
- Prêt à voter sur les 3 boutons disponibles (désactivé — boilerplate)
- Sieste nocturne 2h–6h (comportement humain)
- Cutoff mensuel par site pour laisser le cooldown expirer avant le reset

Architecture duale :
  curl_cffi  → session keep-alive Cloudflare (GET /profile → 200 garanti)
  Selenium   → undetected-chromedriver via Xvfb (captchas dynamiques sur Linux)
"""
import sys
import io
import os
import glob
import importlib.util
import shutil
import tempfile
import re
import time
import random
import threading
import json
import gc
try:
    import resource  # Unix-only (FD limits)
except ImportError:
    resource = None  # Windows fallback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from curl_cffi import requests
from bs4 import BeautifulSoup

# Selenium/UC imports sont lazily chargés dans create_driver() pour éviter
# que UC auto-lance chromedriver au démarrage (crash ARM64 → zombie → exception
# WebDriver 40s plus tard dans le thread principal pendant les votes HTTP-only).
uc = None

from lg_logger import logger, trace, status
from hardware_monitor import monitor, notifier

import psutil

def cleanup_leftover_processes():
    """
    Kills any leftover chromium or chromedriver processes to prevent
    resource leaks (Too many open files) and zombie processes.
    """
    targets = ["chromium", "chromedriver"]
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if any(t in proc.info['name'].lower() for t in targets):
                # On ne tue pas le process actuel s'il s'appelait par erreur pareil
                if proc.info['pid'] == os.getpid():
                    continue
                proc.kill()
                trace(f"Killed leftover process: {proc.info['name']} (PID {proc.info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def _get_open_fd_count() -> int:
    """
    Retourne le nombre de descripteurs de fichiers ouverts par le processus courant.
    Sous Linux, compte les entrées dans /proc/self/fd.
    """
    try:
        return len(os.listdir("/proc/self/fd"))
    except Exception:
        return -1


def _get_fd_soft_limit() -> int:
    """Retourne la limite soft de file descriptors (ulimit -n)."""
    try:
        if resource:
            return resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    except Exception:
        pass
    # Fallback Windows / environnements sans resource
    try:
        import subprocess
        out = subprocess.check_output(["ulimit", "-n"], shell=True, text=True).strip()
        return int(out)
    except Exception:
        return 1024  # default safe guess


def _check_fd_health() -> dict:
    """
    Vérifie la santé des descripteurs de fichiers et retourne un dict.
    Émet un warning si > 70% de la limite est atteinte.
    """
    fd_count  = _get_open_fd_count()
    fd_limit  = _get_fd_soft_limit()
    pct       = (fd_count / fd_limit * 100) if fd_limit > 0 else 0

    health = {
        "fd_open":  fd_count,
        "fd_limit": fd_limit,
        "fd_pct":   round(pct, 1),
        "critical": pct > 90,
        "warning":  pct > 70,
    }

    if health["critical"]:
        status(f"🚨 FD CRITIQUE : {fd_count}/{fd_limit} ouverts ({pct:.1f}%) — "
               "Too many open files imminent !")
    elif health["warning"]:
        status(f"⚠️ FD WARNING : {fd_count}/{fd_limit} ouverts ({pct:.1f}%)")

    return health


def _emergency_fd_cleanup():
    """
    Nettoyage d'urgence des descripteurs de fichiers :
    1. Force le garbage collector Python
    2. Tue tout processus chromium/chromedriver zombie
    3. Réinitialise la session curl_cffi si elle existe
    Doit être appelé avec la session comme argument ou via une closure.
    """
    status("🧹 EMERGENCY FD CLEANUP déclenché...")

    # 1. GC agressif (ferme les sockets/fichiers non référencés)
    gc.collect()
    gc.collect()  # double passe pour les objets avec __del__

    # 2. Tue tous les processus Chrome zombies
    cleanup_leftover_processes()

    # 3. Tente de nettoyer les tmpdirs orphelins
    try:
        for entry in os.listdir(tempfile.gettempdir()):
            if entry.startswith("tmp") and os.path.isdir(os.path.join(tempfile.gettempdir(), entry)):
                try:
                    chromedriver_path = os.path.join(tempfile.gettempdir(), entry, "chromedriver")
                    if os.path.exists(chromedriver_path):
                        shutil.rmtree(os.path.join(tempfile.gettempdir(), entry), ignore_errors=True)
                except Exception:
                    pass
    except Exception:
        pass

    # 4. Log l'état après nettoyage
    health = _check_fd_health()
    status(f"Post-cleanup FD: {health['fd_open']}/{health['fd_limit']} ({health['fd_pct']}%)")
    return health

# ── Encodage UTF-8 forcé ────────────────────────────────────────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

load_dotenv()

# ── Configuration session ────────────────────────────────────────────────────
TARGET_PROFILE_URL = "https://lostgard.fr/profile"
TARGET_VOTE_URL    = "https://lostgard.fr/vote"   # TODO: confirmer l'URL exacte
LG_COOKIE          = os.getenv("LG_COOKIE", "")
LG_USER_AGENT      = os.getenv(
    "LG_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
)
TARGET_PSEUDO    = os.getenv("LG_PSEUDO", "")

# ── Binaires Chromium (Linux ARM64 — Raspberry Pi) ───────────────────────────
CHROMIUM_BIN     = os.getenv("CHROMIUM_BIN",     "/usr/bin/chromium")
CHROMEDRIVER_BIN = os.getenv("CHROMEDRIVER_BIN", "/usr/bin/chromedriver")
DRIVER_LAUNCH_TIMEOUT = 60  # secondes max pour lancer uc.Chrome() avant de considérer un freeze

# ── Persistance des timers ────────────────────────────────────────────────────
STATE_FILE    = "/app/state.json"   # timers sauvegardés entre redémarrages
OVERRIDE_FILE = "/app/reset_sites.json"  # pour forcer le vote d'un site sans redémarrer
CF_TITLES        = ("Just a moment...", "Un instant…", "Attention Required!", "Please Wait...")

# ── Découverte automatique des modules bypass ────────────────────────────────
def _discover_vote_modules() -> dict:
    """
    Scanne le répertoire courant pour tous les fichiers vote_*.py et les importe.
    Le site_id est extrait du nom de fichier : vote_{id}_bypass.py → "{id}".
    Les modules sont triés par nom de fichier (vote_1 avant vote_2, etc.).
    Interface requise : SITE_NAME, COOLDOWN_SECONDS, vote(session, driver).
    """
    directory = os.path.dirname(os.path.abspath(__file__))
    found = {}
    for path in sorted(glob.glob(os.path.join(directory, "vote_*.py"))):
        filename = os.path.basename(path)
        m = re.match(r'^vote_(.+?)(?:_bypass)?\.py$', filename)
        if not m:
            continue
        site_id = m.group(1)
        module_name = filename[:-3]
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            missing = [a for a in ("SITE_NAME", "COOLDOWN_SECONDS", "vote") if not hasattr(mod, a)]
            if missing:
                print(f"[discovery] {filename} ignoré — attributs manquants : {missing}")
                continue
            found[site_id] = mod
            print(f"[discovery] {filename} → site_id={site_id!r}  ({mod.SITE_NAME})")
        except Exception as e:
            print(f"[discovery] Erreur import {filename} : {e}")
    if not found:
        print("[discovery] ATTENTION — aucun module vote_*.py trouvé !")
    return found

BYPASS_MODULES = _discover_vote_modules()

# ── Paramètres sieste nocturne ───────────────────────────────────────────────
NIGHT_START        = 2     # heure de début (incluse)
NIGHT_END          = 6     # heure de fin   (exclue)
NIGHT_SLEEP_CHANCE = 0.90  # 90 % de chance de dormir ; 10 % nuit blanche
MAX_RETRIES        = 3     # tentatives max par bouton si vote échoué

# ── Paramètres stratégie de vote ─────────────────────────────────────────────
MIN_VOTES_LEAD  = 3
MAX_VOTES_LEAD  = 5
LEAD_SLEEP_BASE = 300    # 5 min de base
LEAD_SLEEP_MAX  = 3600   # 1h max

# ── Cutoffs reset mensuel (cooldown du site + marge 10 min, en secondes) ─────
# Valeurs par défaut issues d'autovoteSAO — à ajuster selon les vraies durées
# de cooldown des boutons N1/N2/N3 de lostgard.fr une fois le vote activé.
SITE_CUTOFF = {sid: mod.COOLDOWN_SECONDS for sid, mod in BYPASS_MODULES.items()}
RESET_VOTE_THRESHOLD = 3   # votes max pour considérer le classement resetté


# ────────────────────────────────────────────────────────────────────────────
# Session Cloudflare (curl_cffi — identique au keep-alive actif)
# ────────────────────────────────────────────────────────────────────────────

def create_session() -> requests.Session:
    """
    Crée une Session curl_cffi impersonnant Chrome 124.
    Injecte les cookies via le jar (pas le header Cookie) pour que
    curl_cffi gère correctement le bypass Cloudflare sans cf_clearance.
    """
    session = requests.Session(impersonate="chrome124")
    session.headers.update({
        "User-Agent":      LG_USER_AGENT,
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,"
                           "image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    for part in LG_COOKIE.split(";"):
        part = part.strip()
        if "=" in part:
            name, value = part.split("=", 1)
            name = name.strip()
            if name != "cf_clearance":  # cf_clearance est IP-bound, inutile sur le Pi
                session.cookies.set(name, value.strip(), domain="lostgard.fr")
    return session


def _create_proxy_auth_extension(proxy_host: str, proxy_port: str,
                                 proxy_user: str, proxy_pass: str) -> str:
    """
    Cree une extension Chrome Manifest V3 temporaire qui gere
    l'authentification proxy. Retourne le chemin du dossier temporaire
    (a detruire par l'appelant apres driver.quit()).

    Necessaire car Chromium ne supporte PAS l'authentification proxy
    via la ligne de commande --proxy-server.
    """
    import json as _json
    ext_dir = tempfile.mkdtemp(prefix="proxy_auth_ext_")

    manifest = {
        "version": "1.0.0",
        "manifest_version": 3,
        "name": "Proxy Auth",
        "permissions": ["proxy", "webRequest", "webRequestAuthProvider"],
        "host_permissions": ["<all_urls>"],
        "background": {"service_worker": "background.js"}
    }
    with open(os.path.join(ext_dir, "manifest.json"), "w") as f:
        _json.dump(manifest, f)

    background_js = f"""
chrome.proxy.settings.set({{
    value: {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{proxy_host}",
                port: parseInt("{proxy_port}")
            }},
            bypassList: ["localhost", "127.0.0.1"]
        }}
    }},
    scope: "regular"
}});

chrome.webRequest.onAuthRequired.addListener(
    function(details) {{
        return {{
            authCredentials: {{
                username: "{proxy_user}",
                password: "{proxy_pass}"
            }}
        }};
    }},
    {{urls: ["<all_urls>"]}},
    ["blocking"]
);
"""
    with open(os.path.join(ext_dir, "background.js"), "w") as f:
        f.write(background_js)

    trace(f"Proxy auth extension created at {ext_dir}")
    return ext_dir


def create_driver(proxy: dict | None = None):
    """
    Lance Chromium via undetected-chromedriver (headed via Xvfb sur Linux).

    - Linux/Pi : copie chromedriver depuis CHROMEDRIVER_BIN dans /tmp
      pour que uc puisse le patcher sans toucher au binaire systeme.
    - Windows/Mac : laisse undetected-chromedriver auto-telecharger
      le chromedriver approprie (pas besoin de pre-installer).

    Retourne (driver, tmp_dir) — appelant responsable de driver.quit() + shutil.rmtree(tmp_dir).
    Leve TimeoutError si uc.Chrome() freeze plus de DRIVER_LAUNCH_TIMEOUT secondes.
    Leve RuntimeError si le nombre de FDs est deja critique avant le lancement.

    Args:
        proxy: dict optionnel {"host", "port", "user", "pass"} pour proxy residentiel
    """
    global uc
    if uc is None:
        import undetected_chromedriver as _uc
        uc = _uc

    # Verification FD avant lancement
    fd_health = _check_fd_health()
    if fd_health['critical']:
        _emergency_fd_cleanup()
        fd_health = _check_fd_health()
        if fd_health['critical']:
            raise RuntimeError(
                f"FD still critical after emergency cleanup: "
                f"{fd_health['fd_open']}/{fd_health['fd_limit']}. "
                "Skipping Chromium launch to prevent crash."
            )

    # Nettoyage preventif avant de lancer un nouveau navigateur
    cleanup_leftover_processes()

    # ── Chromedriver resolution ───────────────────────────────────────────
    tmp_dir = None
    cd_path = None

    if os.path.isfile(CHROMEDRIVER_BIN):
        # Linux/Pi: copier dans /tmp pour permettre le patching
        tmp_dir = tempfile.mkdtemp()
        cd_path = os.path.join(tmp_dir, "chromedriver")
        shutil.copy2(CHROMEDRIVER_BIN, cd_path)
        os.chmod(cd_path, 0o755)
        trace(f"Chromedriver copied from {CHROMEDRIVER_BIN} to {cd_path}")
    else:
        # Windows / pas de chromedriver pre-installe:
        # undetected-chromedriver va auto-telecharger la bonne version
        trace(f"CHROMEDRIVER_BIN={CHROMEDRIVER_BIN} not found — "
              "letting uc auto-download chromedriver")

    options = uc.ChromeOptions()

    # ── Browser binary ────────────────────────────────────────────────────
    if os.path.isfile(CHROMIUM_BIN):
        options.binary_location = CHROMIUM_BIN
    elif sys.platform == "win32":
        # uc auto-detects Chrome/Chromium/Brave on Windows
        trace("No CHROMIUM_BIN set — letting uc auto-detect browser")
    else:
        options.binary_location = CHROMIUM_BIN  # try anyway (will fail fast)

    # ── Proxy support ────────────────────────────────────────────────────
    proxy_ext_dir = None  # extension temporaire pour auth proxy (a nettoyer)
    if proxy:
        proxy_host = proxy["host"]
        proxy_port = proxy["port"]
        proxy_str  = f"{proxy_host}:{proxy_port}"
        proxy_user = proxy.get("user")
        proxy_pass = proxy.get("pass")

        if proxy_user and proxy_pass:
            # Proxy avec authentification → extension Chrome requise
            proxy_ext_dir = _create_proxy_auth_extension(
                proxy_host, proxy_port, proxy_user, proxy_pass
            )
            options.add_argument(f"--load-extension={proxy_ext_dir}")
            trace(f"Proxy configure (with auth): {proxy_str}")
            # NE PAS mettre --disable-extensions : on en a besoin !
        else:
            # Proxy sans auth → flag CLI suffit
            options.add_argument(f"--proxy-server=http://{proxy_str}")
            trace(f"Proxy configure (no auth): {proxy_str}")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--lang=fr-FR")
    # Limiter les processus Chromium pour réduire la consommation FD
    if not proxy_ext_dir:
        options.add_argument("--disable-extensions")  # sauf si proxy auth extension
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-gpu")
    # ── Flags Linux-only (crashent sur Windows) ──────────────────────────
    if sys.platform != "win32":
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        # ARM64-specific: le zygote process cause des SIGSEGV sur Pi/Docker ARM64
        options.add_argument("--no-zygote")
        options.add_argument("--disable-webgl")
        options.add_argument("--disable-accelerated-2d-canvas")
        options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-breakpad")
    options.add_argument("--disable-background-mode")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-field-trial-config")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-in-process-stack-traces")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-ipc-flooding-protection")
    # Limiter le cache disque et mémoire
    options.add_argument("--disk-cache-size=0")
    options.add_argument("--media-cache-size=0")

    _result = {}

    def _launch():
        try:
            kwargs = dict(options=options, headless=False)
            if cd_path:
                kwargs["driver_executable_path"] = cd_path
            _result["driver"] = uc.Chrome(**kwargs)
        except Exception as e:
            _result["error"] = e

    t = threading.Thread(target=_launch, daemon=True)
    t.start()
    t.join(timeout=DRIVER_LAUNCH_TIMEOUT)

    if t.is_alive():
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise TimeoutError(
            f"uc.Chrome() a freeze apres {DRIVER_LAUNCH_TIMEOUT}s — "
            "Chromium ou Xvfb probablement mort."
        )

    if "error" in _result:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise _result["error"]

    driver = _result["driver"]
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(60)

    # Log FD après lancement
    post_health = _check_fd_health()
    status(f"Driver lancé — FD: {post_health['fd_open']}/{post_health['fd_limit']} ({post_health['fd_pct']}%)")

    return driver, tmp_dir, proxy_ext_dir


def _check_session(session) -> bool:
    """
    Vérifie que la session est toujours active.
    Retourne True si /profile répond 200 (pas de redirection vers /auth/login).
    """
    try:
        trace("Checking Cloudflare session keep-alive...")
        resp = session.get(TARGET_PROFILE_URL, allow_redirects=False, timeout=10)
        if resp.status_code == 200:
            trace("Session active (200).")
            return True
        status(f"Session expired or redirected (Code: {resp.status_code}).")
        return False
    except Exception as e:
        status(f"Network error during session check: {e}")
        return False


# ────────────────────────────────────────────────────────────────────────────
# Heartbeat Monitoring Thread
# ────────────────────────────────────────────────────────────────────────────

def _heartbeat_worker(stop_event):
    """
    Background thread that logs metrics and hardware status every 1 minute.
    Also checks 2captcha balance occasionally.
    """
    last_balance_check = 0
    status("Heartbeat thread started.")

    while not stop_event.is_set():
        stats = monitor.get_stats()
        now = time.time()

        # Check 2captcha balance every 30 minutes
        balance_msg = ""
        if now - last_balance_check > 1800:
            try:
                api_key = os.getenv("TWOCAPTCHA_API_KEY", "")
                if api_key:
                    from twocaptcha import TwoCaptcha
                    solver = TwoCaptcha(api_key)
                    bal = solver.balance()
                    balance_msg = f" | 2captcha: {bal}$"
                    last_balance_check = now
            except Exception:
                pass

        if stats:
            # FD health
            fd_health = _check_fd_health()
            fd_msg = f" | FD: {fd_health['fd_open']}/{fd_health['fd_limit']} ({fd_health['fd_pct']}%)"
            log_msg = f"[HEARTBEAT] CPU: {stats['cpu']}% | RAM: {stats['ram_pct']}% | Temp: {stats['temp']}°C{fd_msg}{balance_msg}"
            logger.info(log_msg)

            # If high resources or FD critical, notify Discord (Warning)
            if (stats['ram_pct'] > 90
                or (isinstance(stats['temp'], float) and stats['temp'] > 80)
                or fd_health['warning']):
                notifier.send_embed(
                    "🚨 RPI ALERT - RESOURCES HIGH",
                    log_msg,
                    color=0xf1c40f
                )

            # FD critique → nettoyage d'urgence
            if fd_health['critical']:
                _emergency_fd_cleanup()

        # Sleep exactly 60s
        stop_event.wait(60)


# ────────────────────────────────────────────────────────────────────────────
# Reset mensuel
# ────────────────────────────────────────────────────────────────────────────

def _next_midnight_ts() -> float:
    """Timestamp du prochain minuit (00:00:00 demain)."""
    now = datetime.now()
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def _get_next_month_reset() -> datetime:
    """Retourne le datetime du 1er du mois suivant à 00:00:00."""
    now = datetime.now()
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, 0, 0, 0)
    return datetime(now.year, now.month + 1, 1, 0, 0, 0)


def _seconds_until_month_reset() -> float:
    """Secondes restantes avant le reset mensuel (1er du mois à 00:00)."""
    return (_get_next_month_reset() - datetime.now()).total_seconds()


def _is_site_in_cutoff(site_id: str) -> bool:
    """
    Vérifie si un site doit arrêter de voter pour que son cooldown
    expire AVANT le reset mensuel (minuit le 1er).
    """
    secs   = _seconds_until_month_reset()
    cutoff = SITE_CUTOFF.get(site_id, 0)
    return secs <= cutoff


def _is_all_sites_in_cutoff() -> bool:
    """Tous les sites sont en cutoff → on approche de minuit."""
    return all(_is_site_in_cutoff(sid) for sid in SITE_CUTOFF)


def _wait_for_month_reset(session) -> bool:
    """
    Attend le reset mensuel en dormant jusqu'à minuit pile (1er du mois 00:00:00).
    On ne sonde plus le classement — le site peut mettre plusieurs minutes à s'actualiser,
    ce qui retarderait le rush. On vote dès que l'horloge passe minuit.
    """
    reset_dt = _get_next_month_reset()
    print(f"\n[reset] Attente du reset mensuel ({reset_dt.strftime('%d/%m/%Y %H:%M')})...")

    while True:
        secs = _seconds_until_month_reset()
        if secs <= 0:
            print(f"  Minuit atteint — lancement du rush immédiat !")
            return True
        if secs > 60:
            sleep = secs - 2  # réveil 2s avant minuit pour absorber la latence système
            wake_at = datetime.now() + timedelta(seconds=sleep)
            print(f"  Dodo jusqu'à {wake_at.strftime('%d/%m %H:%M:%S')} (~{sleep/3600:.1f}h)...")
            time.sleep(sleep)
        else:
            time.sleep(0.2)  # boucle serrée dans les 60 dernières secondes


def _rush_all_sites(session):
    """
    Exécute un cycle de vote immédiat sur tous les sites activés.
    Utilisé après la détection du reset mensuel.
    """
    print("\n🚀 RUSH MENSUEL — Vote de tous les sites !")
    for site_id, module in BYPASS_MODULES.items():
        if not module.ENABLED:
            continue

        print(f"  [{module.SITE_NAME}] Rush...")
        driver, tmp_dir, proxy_ext_dir = None, None, None
        needs_driver = getattr(module, "NEEDS_DRIVER", True)
        try:
            if needs_driver:
                driver, tmp_dir, proxy_ext_dir = create_driver()
            module.vote(session, driver)
        except Exception as e:
            print(f"  [{module.SITE_NAME}] Erreur Rush : {e}")
        finally:
            if driver:
                try:
                    for handle in driver.window_handles[1:]:
                        driver.switch_to.window(handle)
                        driver.close()
                    if driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
                except Exception:
                    pass
                try:
                    driver.quit()
                except Exception:
                    pass
            if proxy_ext_dir:
                try:
                    shutil.rmtree(proxy_ext_dir, ignore_errors=True)
                except Exception:
                    pass
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

            # FD recovery entre les sites du rush
            cleanup_leftover_processes()
            fd_after = _check_fd_health()
            if fd_after['warning']:
                print(f"  [rush] FD élevé post-{module.SITE_NAME}, attente recovery...")
                deadline = time.time() + 45
                while time.time() < deadline:
                    time.sleep(3)
                    fd_now = _check_fd_health()
                    if fd_now['fd_pct'] < 60:
                        break
                else:
                    _emergency_fd_cleanup()
            else:
                time.sleep(2)  # délai minimum entre sites


# ────────────────────────────────────────────────────────────────────────────
# Scraping du podium et analyse stratégique
# ────────────────────────────────────────────────────────────────────────────

def _scrape_podium(session) -> dict:
    """
    Parse /vote et extrait le classement.
    Structure HTML : div.vote-ranking-entry > span.username + span.votes-count.
    Retourne : {"players": [{"pseudo": str, "votes": int, "position": int}], ...}
    """
    try:
        resp = session.get(TARGET_VOTE_URL, timeout=10)
        if resp.status_code != 200:
            print(f"  [podium] HTTP {resp.status_code} — podium vide.")
            return {"players": [], "timestamp": datetime.now()}

        soup    = BeautifulSoup(resp.text, "html.parser")
        entries = soup.select("div.vote-ranking-entry")
        players = []
        for pos, entry in enumerate(entries, start=1):
            username_el = entry.select_one("span.username")
            votes_el    = entry.select_one("span.votes-count")
            if not username_el or not votes_el:
                continue
            pseudo     = username_el.get_text(strip=True)
            votes_text = votes_el.get_text(strip=True)
            m          = re.match(r"(\d+)", votes_text)
            votes      = int(m.group(1)) if m else 0
            players.append({"pseudo": pseudo, "votes": votes, "position": pos})

        return {"players": players, "timestamp": datetime.now()}
    except Exception as e:
        print(f"  [podium] Erreur scraping : {e}")
        return {"players": [], "timestamp": datetime.now()}


def _analyze_standing(podium: dict) -> dict:
    """
    Analyse la position de TARGET_PSEUDO et retourne la stratégie.

    Returns:
        {
            "position": 1/2/3/0,
            "votes": N,
            "first_place_votes": N,
            "vote_gap": N,
            "strategy": "nuit_blanche" | "dormir_progressif" | "dormir_beaucoup"
        }
    """
    players = podium.get("players", [])

    our_player = next((p for p in players if p["pseudo"] == TARGET_PSEUDO), None)
    if not our_player:
        return {
            "position": 0,
            "votes": 0,
            "first_place_votes": players[0]["votes"] if players else 0,
            "vote_gap": float("-inf"),
            "strategy": "nuit_blanche",
        }

    if our_player["position"] == 1:
        # On est #1 : l'écart se mesure par rapport au #2 (notre avance réelle)
        second_place = next((p for p in players if p["position"] == 2), None)
        first_votes  = second_place["votes"] if second_place else 0
    else:
        first_place = next((p for p in players if p["position"] == 1), None)
        first_votes = first_place["votes"] if first_place else 0
    vote_gap = our_player["votes"] - first_votes

    if our_player["position"] in (0, 2, 3):
        strategy = "nuit_blanche"
        print(f"  {TARGET_PSEUDO} est #{our_player['position']} → NUIT BLANCHE")
    elif vote_gap < MIN_VOTES_LEAD:
        strategy = "nuit_blanche"
        print(f"  {TARGET_PSEUDO} #1 — écart={vote_gap} < {MIN_VOTES_LEAD} → NUIT BLANCHE")
    elif vote_gap <= MAX_VOTES_LEAD:
        strategy = "dormir_progressif"
        print(f"  {TARGET_PSEUDO} #1 — écart={vote_gap} (3-5) → DORMIR PROGRESSIF")
    else:
        strategy = "dormir_beaucoup"
        print(f"  {TARGET_PSEUDO} #1 — écart={vote_gap} > {MAX_VOTES_LEAD} → DORMIR BEAUCOUP")

    return {
        "position":         our_player["position"],
        "votes":            our_player["votes"],
        "first_place_votes": first_votes,
        "vote_gap":         vote_gap,
        "strategy":         strategy,
    }


# ────────────────────────────────────────────────────────────────────────────
# Gestion de la nuit
# ────────────────────────────────────────────────────────────────────────────

def _is_night() -> bool:
    return NIGHT_START <= datetime.now().hour < NIGHT_END


def _seconds_until_morning() -> float:
    now  = datetime.now()
    wake = now.replace(hour=NIGHT_END, minute=0, second=0, microsecond=0)
    if now >= wake:
        wake += timedelta(days=1)
    return (wake - now).total_seconds()


def _handle_night_sleep() -> bool:
    """
    Entre NIGHT_START et NIGHT_END, dort jusqu'à NIGHT_END avec probabilité
    NIGHT_SLEEP_CHANCE. Retourne True si on a dormi (la boucle doit continuer).
    """
    if not _is_night():
        return False
    if random.random() < NIGHT_SLEEP_CHANCE:
        secs    = _seconds_until_morning()
        wake_at = datetime.now() + timedelta(seconds=secs)
        print(f"\nSieste nocturne. Réveil à {wake_at.strftime('%H:%M')} ({secs / 3600:.1f}h).")
        time.sleep(secs)
        return True
    print("Nuit blanche (rare) — on continue.")
    return False


# ────────────────────────────────────────────────────────────────────────────
# Calcul du sleep entre votes
# ────────────────────────────────────────────────────────────────────────────

def _calc_sleep(next_wake_ts: float, strategy: str = "nuit_blanche") -> int:
    """
    Calcule le nombre de secondes à dormir avant le prochain vote.

    - nuit_blanche    : dort jusqu'à next_wake_ts + buffer (jamais de décalage au matin)
    - dormir_progressif : idem, mais peut ajouter un délai stratégique
    - dormir_beaucoup : décale le réveil à NIGHT_END si on est la nuit
    """
    base_sleep = max(0, next_wake_ts - time.time()) + 5   # 5s buffer (précision minuit)

    if strategy == "nuit_blanche":
        return int(base_sleep)

    if strategy in ("dormir_progressif", "dormir_beaucoup"):
        if strategy == "dormir_beaucoup" and _is_night():
            secs = _seconds_until_morning()
            return int(max(base_sleep, secs))
        return int(base_sleep)

    return int(base_sleep)


# ────────────────────────────────────────────────────────────────────────────
# Persistance des timers
# ────────────────────────────────────────────────────────────────────────────

def _load_state() -> dict[str, float]:
    """Charge next_vote_at depuis STATE_FILE. Retourne des timers à 0 si absent/corrompu."""
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        timers = {sid: float(data.get(sid, 0)) for sid in BYPASS_MODULES}
        print(f"[state] Timers chargés depuis {STATE_FILE}")
        for sid, ts in timers.items():
            remaining = max(0, ts - time.time())
            print(f"  Site {sid} : prochain vote dans {int(remaining // 60)} min {int(remaining % 60)}s")
        return timers
    except FileNotFoundError:
        print(f"[state] {STATE_FILE} absent — timers à 0 (vote immédiat).")
    except Exception as e:
        print(f"[state] Erreur chargement : {e} — timers à 0.")
    return {sid: 0.0 for sid in BYPASS_MODULES}


def _save_state(next_vote_at: dict[str, float]) -> None:
    """Sauvegarde next_vote_at dans STATE_FILE."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(next_vote_at, f)
    except Exception as e:
        print(f"[state] Erreur sauvegarde : {e}")


def _apply_midnight_reset(next_vote_at: dict[str, float]) -> None:
    """
    Si le prochain vote était prévu AVANT le dernier minuit, on remet à 0.
    Cela signifie que le site a resetté (reset quotidien) et qu'on a raté le créneau.
    On ne reset PAS les votes prévus dans le futur, même si le dernier vote était hier.
    """
    now_ts = time.time()
    last_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    for site_id, module in BYPASS_MODULES.items():
        ts = next_vote_at.get(site_id, 0)
        if ts <= 0:
            continue
        
        # Si le timer est dans le passé par rapport à minuit
        if ts < last_midnight:
            print(f"[midnight-reset] Site {site_id} ({module.SITE_NAME}) : "
                  f"timer expiré depuis minuit → prêt à voter.")
            next_vote_at[site_id] = 0.0


def _apply_overrides(next_vote_at: dict[str, float]) -> None:
    """
    Lit OVERRIDE_FILE (ex: {"3": 0}) et remet les timers listés à 0 (vote immédiat).
    Supprime le fichier après application pour ne pas boucler.
    Usage : echo '{"3": 0}' > /app/reset_sites.json
    """
    if not os.path.exists(OVERRIDE_FILE):
        return
    try:
        with open(OVERRIDE_FILE, "r") as f:
            overrides = json.load(f)
        for sid, ts in overrides.items():
            if sid in next_vote_at:
                next_vote_at[sid] = float(ts)
                label = "vote immédiat" if float(ts) == 0 else f"dans {int((float(ts)-time.time())//60)} min"
                print(f"[override] Site {sid} → {label}")
        os.remove(OVERRIDE_FILE)
    except Exception as e:
        print(f"[override] Erreur : {e}")

def _send_status_summary(next_vote_at: dict[str, float]):
    """Envoie un récapitulatif des timers de vote à Discord."""
    timers_info = {}
    for sid, module in BYPASS_MODULES.items():
        ts = next_vote_at.get(sid, 0)
        remaining = ts - time.time()
        if remaining <= 0:
            val = "✅ Prêt à voter"
        else:
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            val = f"⏳ Attente : {f'{h}h ' if h > 0 else ''}{m} min"
        timers_info[module.SITE_NAME] = val
    
    notifier.notify_status_summary(timers_info)


# ────────────────────────────────────────────────────────────────────────────
# Boucle principale
# ────────────────────────────────────────────────────────────────────────────

def main():
    status("Starting lostgard_voter Orchestrator...")
    cleanup_leftover_processes()
    
    # ── Start Heartbeat Daemon ──────────────────────────────────────────────
    stop_heartbeat = threading.Event()
    hb_thread = threading.Thread(target=_heartbeat_worker, args=(stop_heartbeat,), daemon=True)
    hb_thread.start()

    notifier.send_embed("🚀 Bot Start", "L'orchestrateur de vote redémarre.", color=0x3498db)

    if not LG_COOKIE:
        print("ERREUR : LG_COOKIE non défini dans .env — arrêt.")
        sys.exit(1)

    session = create_session()

    # Vérification initiale de la session
    if not _check_session(session):
        print("Session inactive au démarrage. Vérifier le cookie dans .env.")
        sys.exit(1)

    # Timers par site : chargés depuis le fichier si disponible
    next_vote_at: dict[str, float] = _load_state()
    _apply_midnight_reset(next_vote_at)
    _send_status_summary(next_vote_at)

    last_strategy = "nuit_blanche"
    session_request_count = 0   # Compteur pour refresh périodique de la session
    SESSION_MAX_REQUESTS  = 30  # Régénérer la session toutes les ~30 requêtes

    while True:
        # ── Overrides externes (reset d'un site sans redémarrer) ─────────────
        _apply_overrides(next_vote_at)
        # ── Reset minuit : invalide les timers basés sur un vote pré-minuit ──
        _apply_midnight_reset(next_vote_at)

        # ── Sieste nocturne (sauf si nuit blanche forcée) ────────────────────
        if last_strategy != "nuit_blanche" and _handle_night_sleep():
            continue

        # ── Vérification keep-alive de la session (curl_cffi) ────────────────
        # Régénération périodique de la session pour éviter l'accumulation
        # de connexions stale dans le pool HTTP (contribue au leak de FDs).
        if session_request_count >= SESSION_MAX_REQUESTS:
            status(f"Session refresh périodique après {session_request_count} requêtes...")
            try:
                session.close()
            except: pass
            session = create_session()
            session_request_count = 0

        if not _check_session(session):
            print("Session expirée — recréation...")
            try:
                session.close() # Libère les descripteurs de fichiers
            except: pass
            session = create_session()
            session_request_count = 0
            if not _check_session(session):
                print("Impossible de récupérer la session. Attente 5 min...")
                time.sleep(300)
                continue

        session_request_count += 1

        # ── Podium + stratégie (désactivé tant que vote non actif) ───────────
        podium   = _scrape_podium(session)
        standing = _analyze_standing(podium)
        last_strategy = standing["strategy"]

        # ── Boucle sur les boutons de vote ───────────────────────────────────
        soonest_wake = time.time() + 300   # fallback : revérifier dans 5 min

        for site_id, module in BYPASS_MODULES.items():
            now = time.time()

            # Timer : site pas encore dispo
            if now < next_vote_at[site_id]:
                soonest_wake = min(soonest_wake, next_vote_at[site_id])
                continue

            # Cutoff mensuel
            if _is_site_in_cutoff(site_id):
                print(f"  [{module.SITE_NAME}] En cutoff mensuel — ignoré.")
                continue

            # Vote — driver Selenium instancié à la demande (un par vote, fermé ensuite)
            print(f"\n  [{module.SITE_NAME}] Lancement...")
            driver, tmp_dir, proxy_ext_dir = None, None, None
            needs_driver = getattr(module, "NEEDS_DRIVER", True)
            try:
                if module.ENABLED and needs_driver:
                    driver, tmp_dir, proxy_ext_dir = create_driver()
                result = module.vote(session, driver)
            except Exception as e:
                reason = str(e)
                # Stale Chromium crash exception leaking into HTTP-only votes.
                # WebDriverException formats as "Message:\nStacktrace:\n#0 0x..."
                # or starts directly with "Stacktrace:\n#0..." — both cases handled.
                if not needs_driver and "Stacktrace:" in reason:
                    first_line = reason.split("\n")[0].strip() or "crash"
                    reason = f"Stale Chrome crash (vote precedent): {first_line}"
                print(f"  [{module.SITE_NAME}] Exception : {reason}")
                result = {"status": "failed", "reason": reason}
            finally:
                if driver:
                    try:
                        # Fermer toutes les fenêtres avant quit
                        try:
                            for handle in driver.window_handles[1:]:
                                driver.switch_to.window(handle)
                                driver.close()
                            if driver.window_handles:
                                driver.switch_to.window(driver.window_handles[0])
                        except Exception:
                            pass
                        driver.quit()
                        trace(f"[{module.SITE_NAME}] Driver fermé.")
                    except Exception:
                        pass
                if proxy_ext_dir:
                    shutil.rmtree(proxy_ext_dir, ignore_errors=True)
                if tmp_dir:
                    shutil.rmtree(tmp_dir, ignore_errors=True)

                # Cleanup leftover processes after each Selenium run
                cleanup_leftover_processes()

                # Attendre la mort complète de Chrome avant le site suivant.
                # Un crash Chromium asynchrone peut lever une WebDriverException
                # dans le thread principal pendant le vote HTTP suivant.
                if driver is not None or needs_driver:
                    chrome_deadline = time.time() + 15
                    while time.time() < chrome_deadline:
                        alive = [p for p in psutil.process_iter(['name'])
                                 if 'chrom' in (p.info.get('name') or '').lower()]
                        if not alive:
                            break
                        time.sleep(1)
                    else:
                        cleanup_leftover_processes()  # kill anything still alive

                # ── CRITIQUE: Délai FD recovery après Selenium ───────────────
                # Les sockets TCP du navigateur entrent en TIME_WAIT (60-120s).
                # Sans ce délai, le prochain lancement Chromium peut échouer
                # avec [Errno 24] Too many open files.
                if driver is not None or needs_driver:
                    fd_after = _check_fd_health()
                    if fd_after['warning']:
                        status(f"[{module.SITE_NAME}] FD élevé post-vote, "
                               f"attente recovery ({fd_after['fd_open']}/{fd_after['fd_limit']})...")
                        # Attente active que les FDs redescendent sous 60%
                        recovery_deadline = time.time() + 60
                        while time.time() < recovery_deadline:
                            time.sleep(3)
                            fd_now = _check_fd_health()
                            if fd_now['fd_pct'] < 60:
                                status(f"[{module.SITE_NAME}] FD recovery OK: "
                                       f"{fd_now['fd_open']}/{fd_now['fd_limit']} ({fd_now['fd_pct']}%)")
                                break
                        else:
                            _emergency_fd_cleanup()
                    else:
                        # Même si tout va bien, petit délai de 3s minimum
                        time.sleep(3)

            status_res = result.get("status")

            midnight_ts = _next_midnight_ts()

            if status_res == "success":
                status(f"[{module.SITE_NAME}] SUCCESS.")
                next_vote_at[site_id] = min(now + module.COOLDOWN_SECONDS, midnight_ts)
                
                # Notification enrichie pour le multi-compte DMC
                msg = "Le vote a été validé avec succès !"
                if site_id == "dmc" and "details" in result:
                    accounts_ok = [d["pseudo"] for d in result["details"] if d.get("status") == "success"]
                    if accounts_ok:
                        msg = f"Votes réussis pour : {', '.join(accounts_ok)}"
                
                notifier.notify_success(module.SITE_NAME, msg)

            elif status_res == "already_voted":
                wait = result.get("wait_seconds", module.COOLDOWN_SECONDS)
                reason = result.get('reason', 'Déjà voté (cooldown)')
                status(f"[{module.SITE_NAME}] Already voted: {reason}. Waiting {wait // 60}m.")
                next_vote_at[site_id] = min(now + wait, midnight_ts)

            elif status_res == "disabled":
                next_vote_at[site_id] = min(now + module.COOLDOWN_SECONDS, midnight_ts)

            else:
                reason = result.get('reason', '?')
                status(f"[{module.SITE_NAME}] FAILED: {reason}")
                next_vote_at[site_id] = now + 300   # retry dans 5 min
                
                # Notify Discord on real failure (not cooldown)
                stats = monitor.get_stats()
                notifier.notify_error(module.SITE_NAME, reason, stats)

            _save_state(next_vote_at)
            soonest_wake = min(soonest_wake, next_vote_at[site_id])

        # ── Résumé d'état après passage sur tous les sites ──────────────────
        _send_status_summary(next_vote_at)

        # ── Cutoff total : attendre le reset mensuel ──────────────────────────
        if _is_all_sites_in_cutoff():
            if _wait_for_month_reset(session):
                _rush_all_sites(session)
            continue

        # ── Calcul du prochain réveil ─────────────────────────────────────────
        sleep_secs = _calc_sleep(soonest_wake, strategy=last_strategy)
        wake_at    = datetime.now() + timedelta(seconds=sleep_secs)
        print(f"\nProchain réveil à {wake_at.strftime('%H:%M:%S')} "
              f"(dans {sleep_secs // 60} min {sleep_secs % 60}s).")
        time.sleep(sleep_secs)


if __name__ == "__main__":
    main()
