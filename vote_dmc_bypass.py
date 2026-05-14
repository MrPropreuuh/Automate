"""
Bypass Vote — demeryamc.fr → serveur-prive.net.
Version visuelle avec undetected-chromedriver (Selenium).

🔄 v3 — Per-account browser isolation:
  - Chaque compte ouvre SON PROPRE navigateur avec SON PROPRE proxy.
  - Le navigateur est ferme entre chaque compte → empeche le leak de FDs.
  - Rotation de proxy depuis proxies.txt + proxy_cooldown.json.
  - NEEDS_DRIVER = False : le module gere ses propres drivers.
  - Utilise le create_driver() de l'orchestrateur via import differe.
"""
import os
import re
import time
import json
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from twocaptcha import TwoCaptcha
from openai import OpenAI

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# ── Configuration ─────────────────────────────────────────────────────────────
SITE_NAME        = "demeryamc.fr (serveur-prive.net)"
VOTE_ID          = "dmc"
BASE_URL         = "https://demeryamc.fr"
LOGIN_URL        = f"{BASE_URL}/user/login"
VOTE_PAGE_URL    = f"{BASE_URL}/vote"
DMC_VOTE_SITE_ID = "2"
COOLDOWN_SECONDS = 5460    # 91 min (cooldown standard 1h30)

SP_VOTE_URL      = "https://serveur-prive.net/minecraft/demeryamc/vote"
SP_SITEKEY       = "MTPublic-42pXmytZe"

ENV_FILE         = os.path.join(os.path.dirname(__file__), ".env")
PROXY_FILE       = os.path.join(os.path.dirname(__file__), "proxies.txt")
PROXY_COOLDOWN_FILE = os.path.join(os.path.dirname(__file__), "proxy_cooldown.json")
DEBUG_DIR        = os.path.join(os.path.dirname(__file__), "debug_logs")

ENABLED          = True
NEEDS_DRIVER     = False   # Le module gere ses propres drivers (un par compte)

# ── FD recovery settings ─────────────────────────────────────────────────────
FD_COOLDOWN_SECS = 8      # delai entre quit() d'un driver et lancement du suivant
PROXY_COOLDOWN_SECS = 300 # 5 min minimum entre deux utilisations du meme proxy

from lg_logger import logger as log


# ──────────────────────────────────────────────────────────────────────────────
# Proxy management
# ──────────────────────────────────────────────────────────────────────────────

def _load_proxies() -> list:
    """Charge les proxies depuis proxies.txt (format ip:port:user:pass)."""
    proxies = []
    try:
        if os.path.exists(PROXY_FILE):
            with open(PROXY_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(":")
                    if len(parts) >= 4:
                        proxies.append({
                            "host": parts[0],
                            "port": parts[1],
                            "user": parts[2],
                            "pass": parts[3],
                        })
    except Exception as e:
        log.warning(f"[DMC] Erreur chargement proxies: {e}")
    return proxies


def _load_proxy_cooldowns() -> dict:
    try:
        if os.path.exists(PROXY_COOLDOWN_FILE):
            with open(PROXY_COOLDOWN_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_proxy_cooldowns(cooldowns: dict) -> None:
    try:
        with open(PROXY_COOLDOWN_FILE, "w") as f:
            json.dump(cooldowns, f)
    except Exception as e:
        log.warning(f"[DMC] Erreur sauvegarde proxy cooldowns: {e}")


def _pick_proxy(account_index: int, all_accounts: int) -> dict | None:
    """
    Selectionne un proxy pour un compte donne.
    Strategie : round-robin sur la liste des proxies, avec cooldown.
    Retourne None si aucun proxy dispo (connexion directe).
    """
    proxies = _load_proxies()
    if not proxies:
        log.info("[DMC] Aucun proxy trouve — connexion directe.")
        return None

    cooldowns = _load_proxy_cooldowns()
    now = time.time()

    available = []
    for p in proxies:
        key = f"{p['host']}:{p['port']}"
        last_used = cooldowns.get(key, 0)
        if now - last_used >= PROXY_COOLDOWN_SECS:
            available.append((key, p, last_used))

    if not available:
        log.warning("[DMC] Tous les proxies en cooldown — utilisation du plus ancien.")
        best_key = min(cooldowns, key=cooldowns.get, default=None) if cooldowns else None
        if best_key:
            for p in proxies:
                if f"{p['host']}:{p['port']}" == best_key:
                    cooldowns[best_key] = now
                    _save_proxy_cooldowns(cooldowns)
                    return p

    available.sort(key=lambda x: x[2])
    idx = account_index % len(available)
    key, proxy, _ = available[idx]

    cooldowns[key] = now
    _save_proxy_cooldowns(cooldowns)

    log.info(f"[DMC] Proxy selectionne: {proxy['host']}:{proxy['port']} (compte {account_index+1}/{all_accounts})")
    return proxy


# ──────────────────────────────────────────────────────────────────────────────
# Safe driver cleanup
# ──────────────────────────────────────────────────────────────────────────────

def _safe_quit_driver(driver, tmp_dir: str | None, account_label: str,
                      proxy_ext_dir: str | None = None) -> None:
    """
    Ferme proprement un driver et nettoie les ressources.
    Avec delai pour laisser les sockets TIME_WAIT s'evacuer.
    """
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
            log.info(f"[DMC] Driver ferme pour {account_label}.")
        except Exception as e:
            log.warning(f"[DMC] Erreur fermeture driver pour {account_label}: {e}")

    if proxy_ext_dir:
        import shutil
        try:
            shutil.rmtree(proxy_ext_dir, ignore_errors=True)
            log.info(f"[DMC] Proxy extension cleaned for {account_label}.")
        except Exception:
            pass

    if tmp_dir:
        import shutil
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    # Delai critique : laisse les sockets TCP TIME_WAIT expirer
    time.sleep(FD_COOLDOWN_SECS)


# ── AI Captcha Solver ────────────────────────────────────────────────────────

def _extract_mtcaptcha_base64(driver):
    """Extrait le base64 de l'image MTCaptcha depuis l'iframe. Retourne (base64_str, driver_a_reseter)."""
    wait = WebDriverWait(driver, 20)
    wait.until(EC.frame_to_be_available_and_switch_to_it(
        (By.CSS_SELECTOR, "iframe[src*='mtcaptcha.com']")
    ))
    captcha_element = wait.until(
        EC.visibility_of_element_located((By.ID, "mtcap-image-1"))
    )
    style = captcha_element.get_attribute("style")
    match = re.search(r'base64,([^"]+)', style)
    if not match:
        log.error("[CAPTCHA] Impossible d'extraire le base64 de l'image.")
        driver.switch_to.default_content()
        return None
    return match.group(1)


_CAPTCHA_PROMPT = (
    "Analyse cette image de CAPTCHA. Elle contient des lettres et/ou des chiffres "
    "deformes et barres. Reponds UNIQUEMENT avec la sequence de caracteres que tu "
    "vois, sans aucune explication, phrase ou formatage."
)


def _call_vision_api(base64_image: str, api_key: str, base_url: str, model: str) -> str:
    """Appelle une API compatible OpenAI vision et retourne le texte du captcha."""
    client = OpenAI(base_url=base_url, api_key=api_key) if base_url else OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": _CAPTCHA_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        ]}],
        max_tokens=30
    )
    return response.choices[0].message.content.strip()


def _solve_captcha_ai(driver, github_token):
    """Resout le MTCaptcha visuel — OpenAI → GitHub Models → 2captcha image."""
    openai_key     = os.getenv("OPENAI_API_KEY", "")
    twocaptcha_key = os.getenv("TWOCAPTCHA_API_KEY", "")

    # Ordre de priorite des solveurs AI (base_url=None → OpenAI standard)
    ai_backends = []
    if openai_key:
        ai_backends.append(("OpenAI gpt-4o-mini", openai_key, None, "gpt-4o-mini"))
    if github_token:
        ai_backends.append(("GitHub Models gpt-4o", github_token,
                            "https://models.inference.ai.azure.com", "gpt-4o"))

    try:
        log.info("[CAPTCHA] Extraction de l'image MTCaptcha...")
        base64_image = _extract_mtcaptcha_base64(driver)
        if not base64_image:
            return None

        # Priorites 1-N : solveurs AI
        for label, key, url, model in ai_backends:
            try:
                log.info(f"[CAPTCHA] Envoi a {label}...")
                text = _call_vision_api(base64_image, key, url, model)
                log.info(f"[CAPTCHA] {label} → '{text}'")
                driver.switch_to.default_content()
                return text
            except Exception as e:
                log.warning(f"[CAPTCHA] {label} echoue: {e}")

        # Fallback : 2captcha workers humains
        if twocaptcha_key and twocaptcha_key not in ("dummy_skip", ""):
            try:
                log.info("[CAPTCHA] Envoi a 2captcha (image)...")
                solver = TwoCaptcha(twocaptcha_key)
                result = solver.normal(file=base64_image)
                text = result["code"].strip()
                log.info(f"[CAPTCHA] 2captcha → '{text}'")
                driver.switch_to.default_content()
                return text
            except Exception as e:
                log.error(f"[CAPTCHA] 2captcha image echoue: {e}")

        log.warning("[CAPTCHA] Aucun solveur disponible.")
        driver.switch_to.default_content()
        return None

    except Exception as e:
        log.error(f"[CAPTCHA] Erreur resolution CAPTCHA : {e}")
        try: driver.switch_to.default_content()
        except: pass
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _solve_mtcaptcha(site_key: str, page_url: str, api_key: str) -> str:
    log.info(f"[DMC] Envoi du MTCaptcha a 2captcha...")
    try:
        solver = TwoCaptcha(api_key)
        result = solver.mtcaptcha(sitekey=site_key, url=page_url)
        token = result["code"]
        log.info(f"[DMC] Captcha resolu ! (token len: {len(token)})")
        return token
    except Exception as e:
        log.error(f"[DMC] Erreur 2captcha: {e}")
        raise RuntimeError(f"Captcha solving failed: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Account management
# ──────────────────────────────────────────────────────────────────────────────

def get_accounts():
    load_dotenv(ENV_FILE)
    accounts = []

    acc1 = {
        "email": os.getenv("DMC_EMAIL"),
        "password": os.getenv("DMC_PASSWORD"),
        "pseudo": os.getenv("DMC_PSEUDO", os.getenv("LG_PSEUDO", "TonYMe"))
    }
    if acc1["email"] and acc1["password"]:
        accounts.append(acc1)

    acc2 = {
        "email": os.getenv("DMC_EMAIL2"),
        "password": os.getenv("DMC_PASSWORD2"),
        "pseudo": os.getenv("DMC_PSEUDO2", "MrPropreuuh")
    }
    if acc2["email"] and acc2["password"]:
        accounts.append(acc2)

    return accounts


# ──────────────────────────────────────────────────────────────────────────────
# Debug helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_debug_artifacts(driver, pseudo: str, step: str, error: Exception = None) -> str:
    """
    Capture screenshot + page source sur erreur.
    Retourne le chemin du dossier de debug.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = os.path.join(DEBUG_DIR, f"{pseudo}_{ts}_{step}")
    os.makedirs(debug_dir, exist_ok=True)

    # Screenshot
    try:
        if driver:
            screenshot_path = os.path.join(debug_dir, "screenshot.png")
            driver.save_screenshot(screenshot_path)
            log.info(f"[DEBUG] Screenshot saved: {screenshot_path}")
    except Exception as e:
        log.warning(f"[DEBUG] Failed to save screenshot: {e}")

    # Page source
    try:
        if driver:
            html_path = os.path.join(debug_dir, "page_source.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            log.info(f"[DEBUG] Page source saved: {html_path}")
    except Exception as e:
        log.warning(f"[DEBUG] Failed to save page source: {e}")

    # Current URL
    try:
        if driver:
            url_path = os.path.join(debug_dir, "current_url.txt")
            with open(url_path, "w", encoding="utf-8") as f:
                f.write(driver.current_url)
    except Exception:
        pass

    # Error traceback
    if error:
        tb_path = os.path.join(debug_dir, "traceback.txt")
        with open(tb_path, "w", encoding="utf-8") as f:
            f.write(f"Error type: {type(error).__name__}\n")
            f.write(f"Error message: {str(error)}\n\n")
            f.write("Full traceback:\n")
            f.write(traceback.format_exc())

    # Browser console logs (if available)
    try:
        if driver:
            logs = driver.get_log("browser")
            if logs:
                console_path = os.path.join(debug_dir, "browser_console.txt")
                with open(console_path, "w", encoding="utf-8") as f:
                    for entry in logs[-50:]:  # last 50 entries
                        f.write(f"[{entry['level']}] {entry['message']}\n")
    except Exception:
        pass

    return debug_dir


# ──────────────────────────────────────────────────────────────────────────────
# Per-account vote logic
# ──────────────────────────────────────────────────────────────────────────────

def _check_driver_alive(driver, pseudo: str) -> bool:
    """Quick health check — is the driver still responsive?"""
    try:
        driver.current_url
        return True
    except WebDriverException as e:
        log.error(f"[{pseudo}] DRIVER DEAD — WebDriverException: {e}")
        return False
    except Exception as e:
        log.error(f"[{pseudo}] DRIVER UNRESPONSIVE — {type(e).__name__}: {e}")
        return False


def vote_for_account(driver, account) -> dict:
    """
    Execute le vote pour UN compte sur UN driver deja lance.
    Le driver est cree et detruit par l'appelant (vote()).

    v3.1 — Debug renforce:
      - screenshot + page source sur chaque erreur
      - traceback complete dans le log
      - verification sante du driver avant chaque operation Selenium
    """
    email = account.get("email")
    password = account.get("password")
    pseudo = account.get("pseudo")
    github_token = os.getenv("GITHUB_TOKEN")

    if not email or not password:
        return {"status": "skipped", "reason": "Credentials missing"}

    log.info(f"--- Debut du vote pour {pseudo} ({email}) ---")

    def _fail(step: str, reason: str, exc: Exception = None) -> dict:
        """Helper: log erreur, sauvegarde artefacts debug, retourne dict echec."""
        log.error(f"[{pseudo}] ECHEC a l'etape '{step}': {reason}")
        if exc:
            log.error(f"[{pseudo}] Exception: {type(exc).__name__}: {exc}")
            log.error(f"[{pseudo}] Traceback:\n{traceback.format_exc()}")
        try:
            debug_path = _save_debug_artifacts(driver, pseudo, step, exc)
            log.info(f"[{pseudo}] Artefacts debug sauvegardes dans: {debug_path}")
        except Exception as de:
            log.warning(f"[{pseudo}] Echec sauvegarde debug: {de}")
        return {"status": "failed", "reason": f"[{step}] {reason}", "pseudo": pseudo}

    # ── Step 0: Driver health check ──────────────────────────────────────────
    if not _check_driver_alive(driver, pseudo):
        return _fail("driver_check", "Driver deja mort avant le debut du vote")

    try:
        wait = WebDriverWait(driver, 15)

        # ── Step 1: Navigate to login page ──────────────────────────────────
        log.info(f"[{pseudo}] Navigation vers login ({LOGIN_URL})...")
        try:
            driver.get(LOGIN_URL)
        except WebDriverException as e:
            return _fail("nav_login", f"Echec navigation vers login: {e}", e)
        except TimeoutException:
            log.warning(f"[{pseudo}] Timeout page login, tentative de rechargement...")
            try:
                driver.execute_script("window.stop();")
                driver.get(LOGIN_URL)
            except Exception as e2:
                return _fail("nav_login_retry", f"Echec rechargement: {e2}", e2)

        time.sleep(3)
        log.info(f"[{pseudo}] URL actuelle: {driver.current_url}")

        # ── Step 2: Check if already logged in ──────────────────────────────
        is_logged_in = False
        try:
            driver.find_element(By.ID, "userDropdown")
            is_logged_in = True
            log.info(f"[{pseudo}] Session deja connectee detectee.")
        except Exception:
            try:
                is_logged_in = "login" not in driver.current_url.lower()
            except Exception:
                is_logged_in = False
            log.info(f"[{pseudo}] Non connecte (is_logged_in={is_logged_in}).")

        if is_logged_in:
            page_lower = ""
            try:
                page_lower = driver.page_source.lower()
            except Exception:
                pass
            if pseudo.lower() not in page_lower:
                log.info(f"[{pseudo}] Session d'un autre compte detectee. Deconnexion...")
                try:
                    found = driver.execute_script("""
                        let forms = document.querySelectorAll('form');
                        for (let f of forms) {
                            if (f.action.includes('/logout') || f.id === 'logout-form') {
                                f.submit();
                                return true;
                            }
                        }
                        return false;
                    """)
                    if not found:
                        dropdown = driver.find_element(By.ID, "userDropdown")
                        driver.execute_script("arguments[0].click();", dropdown)
                        time.sleep(1)
                        logout_link = driver.find_element(By.XPATH, "//a[contains(@href, 'logout')]")
                        driver.execute_script("arguments[0].click();", logout_link)

                    time.sleep(4)
                    log.info(f"[{pseudo}] Deconnexion reussie.")
                except Exception as e:
                    log.warning(f"[{pseudo}] Echec deconnexion standard ({e}), forcage via URL...")
                    driver.get(f"{BASE_URL}/user/logout")
                    time.sleep(2)

                driver.get(LOGIN_URL)
                time.sleep(3)

        # ── Step 3: Login form ──────────────────────────────────────────────
        current_url = ""
        try:
            current_url = driver.current_url.lower()
        except WebDriverException as e:
            return _fail("check_url", f"Driver mort — impossible de lire l'URL: {e}", e)

        log.info(f"[{pseudo}] URL apres nav: {current_url}")
        on_login_page = "login" in current_url or "user/login" in current_url

        if on_login_page:
            log.info(f"[{pseudo}] Tentative de connexion (email={email})...")

            if not _check_driver_alive(driver, pseudo):
                return _fail("pre_login_check", "Driver mort avant saisie du formulaire")

            # Email field
            try:
                email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            except TimeoutException:
                return _fail("find_email_field", "Champ email introuvable (timeout 15s)", None)
            except WebDriverException as e:
                return _fail("find_email_field", f"Driver mort lors de la recherche du champ email: {e}", e)

            try:
                email_input.clear()
                email_input.send_keys(email)
                log.info(f"[{pseudo}] Email saisi.")
            except Exception as e:
                return _fail("fill_email", f"Erreur saisie email: {e}", e)

            # Password field
            try:
                pwd_input = driver.find_element(By.NAME, "password")
                pwd_input.clear()
                pwd_input.send_keys(password)
                log.info(f"[{pseudo}] Mot de passe saisi.")
            except Exception as e:
                return _fail("fill_password", f"Erreur saisie mot de passe: {e}", e)

            # Submit
            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                submit_btn.click()
                log.info(f"[{pseudo}] Bouton submit clique.")
            except Exception as e:
                return _fail("click_submit", f"Erreur clic submit: {e}", e)

            time.sleep(5)
            log.info(f"[{pseudo}] URL apres submit: {driver.current_url}")

        else:
            log.warning(f"[{pseudo}] Pas sur la page login (URL={current_url}). On tente la suite...")

        # ── Step 4: Verify identity ─────────────────────────────────────────
        log.info(f"[{pseudo}] Verification identite sur /profile...")
        try:
            driver.get(f"{BASE_URL}/profile")
        except Exception as e:
            return _fail("nav_profile", f"Echec navigation /profile: {e}", e)

        time.sleep(3)
        page_lower = ""
        try:
            page_lower = driver.page_source.lower()
        except Exception as e:
            return _fail("read_profile", f"Impossible de lire la page profile: {e}", e)

        if pseudo.lower() not in page_lower:
            log.warning(f"[{pseudo}] Pseudo absent du profile, tentative de refresh...")
            driver.refresh()
            time.sleep(3)
            try:
                page_lower = driver.page_source.lower()
            except Exception:
                pass
            if pseudo.lower() not in page_lower:
                _save_debug_artifacts(driver, pseudo, "login_failed")
                return {"status": "failed",
                        "reason": f"Login echoue pour {pseudo}.",
                        "pseudo": pseudo}

        log.info(f"[{pseudo}] Confirme : Connecte sur le compte de {pseudo}.")

        # ── Step 5: Vote page ───────────────────────────────────────────────
        log.info(f"[{pseudo}] Acces a la page de vote...")
        driver.get(VOTE_PAGE_URL)
        time.sleep(5)

        btn = None
        for selector in [f'a[data-vote-id="{DMC_VOTE_SITE_ID}"]', 'a[href*="serveur-prive.net"]']:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue

        if not btn:
            _save_debug_artifacts(driver, pseudo, "btn_not_found")
            return {"status": "failed", "reason": "Bouton de vote introuvable", "pseudo": pseudo}

        # ── Step 6: Timer check ─────────────────────────────────────────────
        timer_text = ""
        try:
            timer_el = btn.find_element(By.CLASS_NAME, 'vote-timer')
            timer_text = timer_el.text.strip()
            if not timer_text:
                timer_text = btn.get_attribute("data-vote-time") or ""
        except:
            pass

        if timer_text and (any(c.isdigit() for c in timer_text) or ":" in timer_text):
            log.info(f"[{pseudo}] SKIP : Ce compte a deja vote (Timer: {timer_text}).")
            return {"status": "already_voted", "reason": f"Timer detecte: {timer_text}", "pseudo": pseudo}

        log.info(f"[{pseudo}] Pret a voter (pas de timer detecte).")
        log.info(f"[{pseudo}] Clic sur le bouton de vote...")
        original_window = driver.current_window_handle
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(1)
        btn.click()

        # ── Step 7: Wait for vote tab ───────────────────────────────────────
        vote_window = None
        try:
            wait.until(EC.number_of_windows_to_be(2))
            for window_handle in driver.window_handles:
                if window_handle != original_window:
                    vote_window = window_handle
                    break
            log.info(f"[{pseudo}] Onglet de vote ouvert.")
        except:
            log.warning(f"[{pseudo}] Le deuxieme onglet n'est pas apparu.")

        # ── Step 8: Serveur-Prive AI captcha ────────────────────────────────
        if vote_window:
            log.info(f"[{pseudo}] Basculement vers l'onglet de vote pour resolution AI...")
            driver.switch_to.window(vote_window)
            time.sleep(3)

            try:
                user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                user_input.clear()
                user_input.send_keys(pseudo)

                solved = False
                for try_ai in range(3):
                    log.info(f"[{pseudo}] Tentative de resolution AI n°{try_ai+1}...")
                    solution = _solve_captcha_ai(driver, github_token)
                    if not solution:
                        log.warning(f"[{pseudo}] Pas de solution AI obtenue.")
                        driver.switch_to.default_content()
                        continue

                    # Switch into MTCaptcha iframe and enter solution
                    try:
                        wait.until(EC.frame_to_be_available_and_switch_to_it(
                            (By.CSS_SELECTOR, "iframe[src*='mtcaptcha.com']")
                        ))
                    except Exception as e:
                        log.warning(f"[{pseudo}] Iframe MTCaptcha introuvable: {e}")
                        driver.switch_to.default_content()
                        continue

                    try:
                        captcha_input = driver.find_element(By.ID, "mtcap-inputtext-1")
                        captcha_input.clear()
                        captcha_input.send_keys(solution)
                        log.info(f"[{pseudo}] Solution AI '{solution}' saisie.")
                    except Exception as e:
                        log.warning(f"[{pseudo}] Erreur saisie captcha: {e}")
                        driver.switch_to.default_content()
                        continue

                    # Switch out and wait for captcha auto-validation
                    driver.switch_to.default_content()
                    time.sleep(2)

                    # Click "Je vote maintenant" button
                    try:
                        vote_btn = driver.find_element(By.ID, "voteBtn")
                    except:
                        try:
                            vote_btn = driver.find_element(By.XPATH,
                                "//button[contains(text(), 'Je vote maintenant')]")
                        except:
                            vote_btn = driver.find_element(By.CSS_SELECTOR,
                                '#voteForm button[type="submit"]')

                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", vote_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", vote_btn)
                    log.info(f"[{pseudo}] Bouton 'Je vote maintenant' clique.")
                    time.sleep(3)

                    # Check for captcha error
                    captcha_error = False
                    try:
                        alert_danger = driver.find_element(By.CSS_SELECTOR, '.alert.alert-danger')
                        alert_text = alert_danger.text
                        if "captcha" in alert_text.lower():
                            log.warning(f"[{pseudo}] Erreur captcha detectee: '{alert_text.strip()}'")
                            captcha_error = True
                    except Exception:
                        pass

                    if captcha_error:
                        log.info(f"[{pseudo}] Captcha incorrect — nouvelle tentative...")
                        continue

                    # No captcha error = success
                    log.info(f"[{pseudo}] Vote soumis avec succes (pas d'erreur captcha).")
                    solved = True
                    break

                if not solved:
                    log.error(f"[{pseudo}] Echec de la resolution AI apres 3 tentatives.")
            except Exception as e:
                log.error(f"[{pseudo}] Erreur lors de l'action sur SP : {e}")
                log.error(f"[{pseudo}] Traceback SP: {traceback.format_exc()}")

            driver.switch_to.window(original_window)

        # ── Step 9: Polling validation ──────────────────────────────────────
        log.info(f"[{pseudo}] Attente de la validation dynamique sur Demerya (60s max)...")
        start_poll = time.time()
        validated = False
        while time.time() - start_poll < 60:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, f'a[data-vote-id="{DMC_VOTE_SITE_ID}"]')
                timer_el = btn.find_element(By.CSS_SELECTOR, '.vote-timer')
                current_timer = timer_el.text.strip()

                if current_timer and any(c.isdigit() for c in current_timer):
                    log.info(f"[{pseudo}] SUCCES ! Timer detecte : {current_timer}")
                    validated = True
                    break

                alerts = driver.find_elements(By.CSS_SELECTOR, '.alert-success')
                if alerts and alerts[0].is_displayed():
                    log.info(f"[{pseudo}] SUCCES ! Alerte de succes detectee.")
                    validated = True
                    break

            except:
                pass
            time.sleep(5)

        # ── Step 10: Cleanup vote tab ───────────────────────────────────────
        if vote_window:
            try:
                driver.switch_to.window(vote_window)
                driver.close()
                log.info(f"[{pseudo}] Fermeture de l'onglet de vote.")
            except:
                pass

        try:
            driver.switch_to.window(original_window)
        except Exception:
            pass

        if validated:
            return {"status": "success", "pseudo": pseudo}

        return {"status": "failed",
                "reason": "Timeout : Demerya n'a pas valide le vote",
                "pseudo": pseudo}

    except Exception as e:
        return _fail("top_level", f"Exception non geree: {str(e)}", e)


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point — cree un driver par compte avec proxy dedie
# ──────────────────────────────────────────────────────────────────────────────

def vote(session=None, driver=None) -> dict:
    """
    Point d'entree principal appele par l'orchestrateur.

    v3 — IGNORE le parametre 'driver' externe.
    Cree UN navigateur Chromium PAR compte, avec un proxy different.
    Utilise le create_driver() de l'orchestrateur via import differe
    (evite la duplication de code et la circularite d'import).
    Ferme le navigateur entre chaque compte pour liberer les FDs.
    """
    # Import differe pour eviter la circularite (lostgard_voter importe vote_dmc_bypass)
    from lostgard_voter import create_driver as _create_driver

    accounts = get_accounts()
    if not accounts:
        return {"status": "failed", "reason": "Aucun compte configure"}

    results = []
    any_success = False

    # Nettoyage prealable des processus zombies
    try:
        from lostgard_voter import cleanup_leftover_processes
        cleanup_leftover_processes()
    except Exception:
        pass

    for idx, acc in enumerate(accounts):
        pseudo = acc.get("pseudo", f"compte_{idx}")
        driver = None
        tmp_dir = None
        proxy_ext_dir = None

        try:
            # ── Selection du proxy pour ce compte ────────────────────────────
            proxy = _pick_proxy(idx, len(accounts))

            # ── Lancement du navigateur via l'orchestrateur ──────────────────
            log.info(f"[DMC] Lancement navigateur pour {pseudo} "
                     f"(compte {idx+1}/{len(accounts)})...")
            driver, tmp_dir, proxy_ext_dir = _create_driver(proxy=proxy)

            # ── Execution du vote ────────────────────────────────────────────
            res = vote_for_account(driver, acc)
            results.append(res)
            if res.get("status") == "success":
                any_success = True

        except Exception as e:
            log.error(f"[DMC] Erreur critique pour le compte {pseudo}: {e}")
            results.append({"status": "failed", "reason": str(e), "pseudo": pseudo})

        finally:
            # ── Fermeture propre du driver + delai FD recovery ───────────────
            _safe_quit_driver(driver, tmp_dir, pseudo, proxy_ext_dir)

            # ── Cleanup des processus zombies ────────────────────────────────
            try:
                from lostgard_voter import cleanup_leftover_processes
                cleanup_leftover_processes()
            except Exception:
                pass

    # Resultat global
    if any_success:
        return {"status": "success", "details": results}
    else:
        reason = results[0].get("reason", "Echec inconnu") if results else "Aucun resultat"
        return {"status": results[0].get("status", "failed") if results else "failed",
                "reason": reason,
                "details": results}


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print(f"--- Starting {SITE_NAME} Multi-Account ---")

    # ── Windows: auto-detect browser paths ───────────────────────────────────
    if sys.platform == "win32":
        if not os.getenv("CHROMIUM_BIN"):
            for candidate in [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]:
                if os.path.exists(candidate):
                    os.environ["CHROMIUM_BIN"] = candidate
                    print(f"[test] Auto-detected browser: {candidate}")
                    break
        if not os.getenv("CHROMEDRIVER_BIN"):
            print("[test] No CHROMEDRIVER_BIN set — uc will auto-download chromedriver.")
            print("[test] (First launch may take ~30s to download)")

    result = vote()
    print(f"\nResultat final : {result}")
