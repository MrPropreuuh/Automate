FROM python:3.11-slim-bookworm

# ── Dépendances système ───────────────────────────────────────────────────────
# chromium + chromedriver : captchas dynamiques via undetected-chromedriver
# xvfb : écran virtuel pour headed mode (moins détectable que headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        xvfb \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Répertoire de travail ─────────────────────────────────────────────────────
WORKDIR /app

# ── Dépendances Python ────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Code source ───────────────────────────────────────────────────────────────
COPY lostgard_voter.py lg_logger.py hardware_monitor.py ./
# Tous les modules vote_*.py sont copiés automatiquement — ajouter un site
# = créer vote_{id}_bypass.py ici, pas besoin de toucher ce fichier.
COPY vote_*_bypass.py ./
COPY proxies.txt .
COPY proxy_cooldown.json .
COPY .env .

# ── Variables d'environnement ─────────────────────────────────────────────────
# DISPLAY :99 utilisé par Xvfb (Chromium croit avoir un vrai écran)
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# ── Entrypoint ────────────────────────────────────────────────────────────────
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
