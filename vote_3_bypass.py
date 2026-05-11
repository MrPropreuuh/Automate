"""
Bypass Vote N3 — Serveur-Minecraft.com (bouton 3 de lostgard.fr).
Stratégie : HTTP pur via curl_cffi (bypass Cloudflare) + 2captcha.
Pas de Selenium — le driver ARM64 crash sur ce domaine.
"""
import os
import re
import time

import requests as req
from curl_cffi import requests as cffi_req
from lg_logger import logger, trace, status

SITE_NAME        = "Serveur-Minecraft.com"
VOTE_ID          = "3"
VOTE_URL         = "https://serveur-minecraft.com/5616"
LOGIN_URL        = "https://serveur-minecraft.com/login"
LOGIN_CHECK_URL  = "https://serveur-minecraft.com/login_check"
COOLDOWN_SECONDS = 10860   # 181 min (site cooldown = 180 min)
FALLBACK_SITEKEY = "6LcQmooUAAAAAEuP2PMGi8ZN7OT373Qic8jwgaOX"

ENABLED      = True
NEEDS_DRIVER = False   # vote entièrement HTTP — pas de Selenium (crash ARM64 Chromium)

_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
}


def _solve_2captcha(site_key: str, page_url: str, api_key: str) -> str:
    resp = req.post("https://2captcha.com/in.php", data={
        "key":       api_key,
        "method":    "userrecaptcha",
        "googlekey": site_key,
        "pageurl":   page_url,
        "json":      1,
    }, timeout=15)
    data = resp.json()
    if data.get("status") != 1:
        raise Exception(f"2captcha soumission échouée : {data}")
    task_id = data["request"]
    trace(f"2captcha task {task_id}, waiting for resolution...")
    for i in range(30):
        time.sleep(5)
        trace(f"Polling 2captcha result (attempt {i+1})...")
        r = req.get("https://2captcha.com/res.php", params={
            "key": api_key, "action": "get", "id": task_id,
        }, timeout=15)
        text = r.text.strip()
        if text == "CAPCHA_NOT_READY":
            continue
        if text.startswith("OK|"):
            return text[3:]
        raise Exception(f"2captcha erreur : {text}")
    raise Exception("2captcha timeout (2 min)")


def _make_session() -> cffi_req.Session:
    s = cffi_req.Session(impersonate="chrome124")
    s.headers.update(_HEADERS)
    return s


def _login(s: cffi_req.Session) -> dict:
    """GET /login → extrait le CSRF → POST /login_check. Retourne {} si OK."""
    email    = os.getenv("SM_EMAIL", "")
    password = os.getenv("SM_PASSWORD", "")
    if not email or not password:
        return {"status": "failed", "reason": "SM_EMAIL ou SM_PASSWORD non défini dans .env"}

    # Visite la page de vote d'abord pour obtenir le cf_clearance cookie
    trace(f"{SITE_NAME}: GET {VOTE_URL} (warm-up CF clearance)...")
    s.get(VOTE_URL, timeout=20, allow_redirects=True)

    trace(f"{SITE_NAME}: GET /login...")
    r = s.get(LOGIN_URL, timeout=20)
    if r.status_code != 200:
        return {"status": "failed", "reason": f"GET /login → {r.status_code}"}

    m = re.search(r'name="_csrf_token"\s+value="([^"]+)"', r.text)
    if not m:
        return {"status": "failed", "reason": "CSRF token introuvable sur /login"}
    csrf = m.group(1)

    trace(f"{SITE_NAME}: POST /login_check...")
    r2 = s.post(LOGIN_CHECK_URL, data={
        "_username":   email,
        "_password":   password,
        "_csrf_token": csrf,
    }, allow_redirects=True, timeout=20)

    if "/login" in r2.url:
        snippet = r2.text[:200].replace("\n", " ") if r2.text else "(vide)"
        return {"status": "failed", "reason": f"Login échoué (url={r2.url}) | {snippet}"}

    cookie_names = list(dict(s.cookies).keys())
    status(f"{SITE_NAME}: Login OK → {r2.url} (HTTP {r2.status_code}) | cookies={cookie_names}")
    # Retourne le contenu de la réponse finale si on est déjà sur la page de vote
    return {"_page_html": r2.text, "_page_url": r2.url, "_page_status": r2.status_code}


def vote(session, driver=None) -> dict:
    pseudo  = os.getenv("LG_PSEUDO", "")
    api_key = os.getenv("TWOCAPTCHA_API_KEY", "")
    if not pseudo:
        return {"status": "failed", "reason": "LG_PSEUDO non défini"}
    if not api_key:
        return {"status": "failed", "reason": "TWOCAPTCHA_API_KEY non défini"}

    with _make_session() as s:
        # ── Login ─────────────────────────────────────────────────────────────────
        login_info = _login(s)
        if "status" in login_info:   # dict d'erreur
            return login_info

        # Après login, le serveur redirige souvent directement vers la page de vote
        html = login_info.get("_page_html", "")
        post_login_url = login_info.get("_page_url", "")

        # Vérifier que la page reçue est bien 200 (pas 403 sur le redirect)
        page_status = login_info.get("_page_status", 0)
        if page_status != 200:
            snippet = html[:200].replace("\n", " ") if html else "(vide)"
            return {"status": "failed", "reason": f"Page post-login HTTP {page_status} sur {post_login_url} | {snippet}"}

        # Si le login n'a pas abouti sur la page de vote, on fait un GET explicite
        if VOTE_URL not in post_login_url or not html:
            trace(f"{SITE_NAME}: GET {VOTE_URL}...")
            r = s.get(VOTE_URL, timeout=20)
            if r.status_code != 200:
                snippet = r.text[:300].replace("\n", " ") if r.text else "(vide)"
                return {"status": "failed", "reason": f"GET vote page → {r.status_code} | {snippet}"}
            html = r.text

        # Déjà voté ?
        if any(w in html for w in ("déjà voté", "already voted", "Vous devez attendre")):
            m_h   = re.search(r'(\d+)\s*h',   html)
            m_min = re.search(r'(\d+)\s*min', html)
            wait_secs = (
                (int(m_h.group(1))   * 3600 if m_h   else 0) +
                (int(m_min.group(1)) * 60   if m_min else 0)
            ) or COOLDOWN_SECONDS
            return {"status": "already_voted", "wait_seconds": wait_secs}

        # ── Extraire le sitekey reCAPTCHA ─────────────────────────────────────────
        m_key = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
        site_key = m_key.group(1) if m_key else FALLBACK_SITEKEY
        trace(f"{SITE_NAME}: sitekey={site_key}")

        # ── Extraire tous les champs cachés du formulaire de vote ─────────────────
        form_inputs = dict(re.findall(
            r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"', html
        ))
        form_inputs.update(dict(re.findall(
            r'<input[^>]+value="([^"]*)"[^>]+name="([^"]+)"', html
        )))
        # Extraire l'action du formulaire
        m_action = re.search(r'<form[^>]+action="([^"]+)"', html)
        form_action = m_action.group(1) if m_action else VOTE_URL
        if form_action.startswith("/"):
            form_action = "https://serveur-minecraft.com" + form_action
        # Log du bloc form pour voir exactement ce qui est dans la page
        m_form_block = re.search(r'<form[^>]*action[^>]*>.*?</form>', html, re.DOTALL | re.IGNORECASE)
        form_block_snippet = m_form_block.group(0)[:600].replace("\n"," ") if m_form_block else html[:400].replace("\n"," ")
        status(f"{SITE_NAME}: form action={form_action} | hidden fields={list(form_inputs.keys())} | form_html={form_block_snippet}")

        # ── Résoudre le reCAPTCHA ─────────────────────────────────────────────────
        status(f"{SITE_NAME}: Solving reCAPTCHA via 2captcha...")
        try:
            token = _solve_2captcha(site_key, VOTE_URL, api_key)
        except Exception as e:
            return {"status": "failed", "reason": f"2captcha : {e}"}
        trace("reCAPTCHA token obtenu.")

        # ── POST le vote ──────────────────────────────────────────────────────────
        post_data = dict(form_inputs)   # inclut tous les champs cachés (CSRF etc.)
        # Champ username : essayer les deux noms courants
        post_data["form[username]"] = pseudo
        post_data["form_username"]  = pseudo
        post_data["g-recaptcha-response"] = token

        status(f"{SITE_NAME}: POST vote → {form_action} | fields={list(post_data.keys())}")
        r2 = s.post(form_action, data=post_data, allow_redirects=True, timeout=20)
        snippet2 = r2.text[:300].replace("\n", " ") if r2.text else "(vide)"
        status(f"{SITE_NAME}: POST réponse HTTP {r2.status_code} | {snippet2}")
        resp_html = r2.text

        # ── Lire le résultat ──────────────────────────────────────────────────────
        if 'alert-success' in resp_html:
            m_msg = re.search(r'alert-success[^>]*>(.*?)</div>', resp_html, re.DOTALL)
            msg = re.sub(r'<[^>]+>', '', m_msg.group(1)).strip() if m_msg else "OK"
            print(f"  [{SITE_NAME}] Succès : {msg[:80]}")
            return {"status": "success"}

        for marker in ("alert-danger", "alert-warning"):
            if marker in resp_html:
                m_msg = re.search(rf'{marker}[^>]*>(.*?)</div>', resp_html, re.DOTALL)
                msg = re.sub(r'<[^>]+>', '', m_msg.group(1)).strip() if m_msg else resp_html[:120]
                print(f"  [{SITE_NAME}] Message : {msg[:120]}")
                h     = re.search(r'(\d+)\s*h',   msg)
                m_min = re.search(r'(\d+)\s*min', msg)
                s_sec = re.search(r'(\d+)\s*s\b', msg)
                wait_secs = (
                    (int(h.group(1))     * 3600 if h     else 0) +
                    (int(m_min.group(1)) * 60   if m_min else 0) +
                    (int(s_sec.group(1))         if s_sec else 0)
                ) or COOLDOWN_SECONDS
                if any(w in msg.lower() for w in ("déjà", "already", "heure", "attendre")):
                    return {"status": "already_voted", "wait_seconds": wait_secs, "reason": msg}
                return {"status": "failed", "reason": msg}

        return {"status": "failed", "reason": f"résultat inconnu (HTTP {r2.status_code})"}
