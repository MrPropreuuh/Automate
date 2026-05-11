"""
Bypass Vote N2 — Serveurs Minecraft.org (bouton 2 de lostgard.fr).
Flux : page → clic bouton modal → 2captcha token → injection JS → Confirmer le vote.
Porté depuis autovoteSAO/serveursminecraft_bypass.py (version qui fonctionne).
"""
import os
import re
import time
import random
from datetime import datetime

import requests as req
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from lg_logger import logger, trace, status

SITE_NAME        = "Serveurs Minecraft.org"
VOTE_ID          = "2"
VOTE_URL         = "https://www.serveursminecraft.org/serveur/7294/"
COOLDOWN_SECONDS = 87000   # 24h + 10 min buffer

ENABLED = True


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


def _inject_recaptcha_token(driver, token: str):
    driver.execute_script("""
        var token = arguments[0];
        var el = document.getElementById('g-recaptcha-response');
        if (el) {
            el.style.display = 'block';
            el.style.visibility = 'visible';
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value').set;
            setter.call(el, token);
            el.dispatchEvent(new Event('input',  {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }
        try {
            var cfg = window.___grecaptcha_cfg;
            if (cfg && cfg.clients) {
                Object.keys(cfg.clients).forEach(function(id) {
                    var c = cfg.clients[id];
                    Object.keys(c).forEach(function(k) {
                        var obj = c[k];
                        if (obj && typeof obj.callback === 'function') {
                            obj.callback(token);
                        }
                    });
                });
            }
        } catch(e) {}
    """, token)


def _find_page_message(driver) -> str:
    for selector in (
        "div.alert-success", "div.alert-danger", "div.alert-warning",
        ".alert", "p.text-success", "p.text-danger",
    ):
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            txt = el.text.strip()
            if txt:
                return txt
        except NoSuchElementException:
            continue
    return ""


def vote(session, driver=None) -> dict:
    pseudo  = os.getenv("LG_PSEUDO", "")
    api_key = os.getenv("TWOCAPTCHA_API_KEY", "")
    if not pseudo:
        return {"status": "failed", "reason": "LG_PSEUDO non défini"}
    if not api_key:
        return {"status": "failed", "reason": "TWOCAPTCHA_API_KEY non défini"}
    if driver is None:
        return {"status": "failed", "reason": "driver requis"}

    try:
        trace(f"Navigating to {VOTE_URL}")
        driver.set_page_load_timeout(30)
        driver.get(VOTE_URL)
        wait = WebDriverWait(driver, 15)
        time.sleep(random.uniform(1.5, 3.0))

        # ── Ouvrir la modal de vote ───────────────────────────────────────────
        vote_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a[data-target='#vote']")
        ))
        ActionChains(driver).move_to_element(vote_btn).pause(
            random.uniform(0.3, 0.6)).click().perform()
        time.sleep(random.uniform(0.8, 1.5))

        # ── Remplir le pseudo ─────────────────────────────────────────────────
        pseudo_field = wait.until(EC.visibility_of_element_located((By.ID, "pseudo")))
        pseudo_field.clear()
        pseudo_field.send_keys(pseudo)

        # ── Récupérer le sitekey et résoudre via 2captcha ────────────────────
        trace("Looking for reCAPTCHA sitekey...")
        try:
            el       = driver.find_element(By.CSS_SELECTOR, ".g-recaptcha[data-sitekey]")
            site_key = el.get_attribute("data-sitekey")
        except NoSuchElementException:
            trace("Sitekey not found in .g-recaptcha, checking page source...")
            m = re.search(r'data-sitekey=["\']([^"\']+)["\']', driver.page_source)
            site_key = m.group(1) if m else "6LegdhkUAAAAAJG95xpN69eylHs3bT4wRikdDQzH"

        status(f"{SITE_NAME}: Solving reCAPTCHA via 2captcha...")
        token = _solve_2captcha(site_key, VOTE_URL, api_key)
        trace("reCAPTCHA solved. Injecting token...")
        _inject_recaptcha_token(driver, token)
        trace("Token injected.")
        time.sleep(random.uniform(0.5, 1.0))

        # ── Confirmer le vote ─────────────────────────────────────────────────
        confirm_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[type='submit'][value='Confirmer le vote']")
        ))
        ActionChains(driver).move_to_element(confirm_btn).pause(
            random.uniform(0.3, 0.7)).click().perform()
        time.sleep(4)

        # ── Lire le résultat ──────────────────────────────────────────────────
        msg = _find_page_message(driver)
        print(f"  [{SITE_NAME}] Réponse : '{msg[:120]}'")

        msg_lower = msg.lower()
        already   = ["déjà voté", "already voted", "revenir dans", "come back", "24 h", "24h",
                    "vous avez", "vous devez attendre", "attendre le"]
        success   = ["merci", "vote pris en compte", "bien voté", "enregistré", "félicitations", "success"]

        if any(k in msg_lower for k in already):
            # Tente de parser "le JJ/MM/AAAA HH:MM" pour calculer l'attente exacte
            wait_secs = COOLDOWN_SECONDS
            m_dt = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})', msg)
            if m_dt:
                try:
                    unlock_dt = datetime.strptime(
                        f"{m_dt.group(1)} {m_dt.group(2)}", "%d/%m/%Y %H:%M"
                    )
                    delta = (unlock_dt - datetime.now()).total_seconds()
                    if 0 < delta < COOLDOWN_SECONDS:
                        wait_secs = int(delta) + 60  # +60s buffer
                except ValueError:
                    pass
            return {"status": "already_voted", "wait_seconds": wait_secs, "reason": msg}
        if any(k in msg_lower for k in success):
            return {"status": "success"}

        # Pas de message d'erreur clair → supposé succès (comportement autovoteSAO)
        print(f"  [{SITE_NAME}] Message inconnu — supposé succès.")
        return {"status": "success"}

    except Exception as e:
        return {"status": "failed", "reason": str(e)}
