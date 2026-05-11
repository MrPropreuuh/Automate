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
COPY lostgard_voter.py .
COPY vote_1_bypass.py .
COPY vote_2_bypass.py .
COPY vote_3_bypass.py .
COPY vote_dmc_bypass.py .
COPY lg_logger.py .
COPY hardware_monitor.py .
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
