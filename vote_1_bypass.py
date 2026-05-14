"""
Bypass Vote N1 — Serveur Privé (bouton 1 de lostgard.fr).
MTCaptcha résolu via 2captcha API, puis soumission AJAX.
"""
import os
import re
import time

import requests as req
from twocaptcha import TwoCaptcha
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from lg_logger import logger, trace, status

SITE_NAME        = "Serveur Privé"
VOTE_ID          = "1"
VOTE_URL         = "https://serveur-prive.net/minecraft/lostgard/vote"
FORM_URL         = "https://serveur-prive.net/minecraft/lostgard/vote/form/ajax"
COOLDOWN_SECONDS = 5460    # 91 min (site cooldown = 90 min)
MT_SITEKEY       = "MTPublic-42pXmytZe"

ENABLED      = True
NEEDS_DRIVER = False   # vote entièrement HTTP — pas de Selenium


def vote(session, driver=None) -> dict:
    pseudo     = os.getenv("LG_PSEUDO", "")
    api_key    = os.getenv("TWOCAPTCHA_API_KEY", "")
    if not pseudo:
        return {"status": "failed", "reason": "LG_PSEUDO non défini"}
    if not api_key:
        return {"status": "failed", "reason": "TWOCAPTCHA_API_KEY non défini"}

    try:
        # ── 1. Récupérer le CSRF token + cookies ─────────────────────────────
        page_resp = req.get(
            VOTE_URL,
            headers={"User-Agent": os.getenv("LG_USER_AGENT", "Mozilla/5.0")},
            timeout=15,
        )
        from bs4 import BeautifulSoup
        soup   = BeautifulSoup(page_resp.text, "html.parser")
        token_el = soup.find("input", {"name": "_token"})
        if not token_el:
            return {"status": "failed", "reason": "CSRF token introuvable"}
        csrf_token = token_el["value"]
        cookies    = page_resp.cookies

        # ── 2. Résoudre MTCaptcha via 2captcha ───────────────────────────────
        status(f"{SITE_NAME}: Solving MTCaptcha via 2captcha...")
        solver = TwoCaptcha(api_key)
        result = solver.mtcaptcha(
            sitekey=MT_SITEKEY,
            url=VOTE_URL,
        )
        mt_token = result["code"]
        trace(f"[{SITE_NAME}] MTCaptcha résolu.")

        # ── 3. Soumettre le formulaire ────────────────────────────────────────
        resp = req.post(
            FORM_URL,
            headers={
                "User-Agent":       os.getenv("LG_USER_AGENT", "Mozilla/5.0"),
                "Referer":          VOTE_URL,
                "X-Requested-With": "XMLHttpRequest",
                "Accept":           "application/json, text/javascript, */*",
            },
            cookies=cookies,
            data={
                "_token":                    csrf_token,
                "username":                  pseudo,
                "ip_code":                   "",
                "mtcaptcha-verifiedtoken":   mt_token,
            },
            timeout=15,
        )

        try:
            body = resp.json()
        except Exception:
            body = {}

        if body.get("success"):
            return {"status": "success"}

        messages = " ".join(str(m).lower() for m in body.get("data", []))
        if any(w in messages for w in ("déjà", "already", "cooldown")):
            wait_secs = COOLDOWN_SECONDS
            m_t = re.search(
                r'prochain vote dans\s*'
                r'(?:(\d+)\s*heure[s]?\s*)?'
                r'(?:(\d+)\s*minute[s]?\s*)?'
                r'(?:(\d+)\s*seconde[s]?)?',
                messages,
            )
            if m_t and any(m_t.groups()):
                total = (int(m_t.group(1) or 0) * 3600
                         + int(m_t.group(2) or 0) * 60
                         + int(m_t.group(3) or 0))
                if total > 0:
                    wait_secs = total + 30
                    trace(f"[{SITE_NAME}] Cooldown exact : {total}s → réveil dans {wait_secs}s.")
            return {"status": "already_voted", "wait_seconds": wait_secs, "reason": messages}
        if any(w in messages for w in ("captcha",)):
            return {"status": "failed", "reason": f"captcha rejeté : {messages}"}

        return {"status": "failed", "reason": messages or resp.text[:200]}

    except TimeoutException:
        return {"status": "failed", "reason": "timeout"}
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
