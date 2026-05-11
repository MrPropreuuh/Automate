#!/bin/bash

# Augmente la limite de fichiers ouverts pour eviter [Errno 24]
# Essayer de monter jusqu'a 65535, avec fallback progressif
for limit in 65535 32768 16384 8192 4096; do
    if ulimit -n "$limit" 2>/dev/null; then
        actual=$(ulimit -n)
        echo "[entrypoint] FD soft limit set to $actual (requested $limit)"
        break
    fi
done

# Si on n'a pas reussi a monter, afficher l'etat actuel
current_limit=$(ulimit -n)
echo "[entrypoint] Final FD soft limit: $current_limit"
if [ "$current_limit" -lt 4096 ]; then
    echo "[entrypoint] ⚠️ WARNING: FD limit is low ($current_limit)."
    echo "[entrypoint] Consider running Docker with: --ulimit nofile=65535:65535"
fi

# Nettoyage lock Xvfb eventuel
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

# Nettoyage des processus Chrome orphelins avant de demarrer
pkill -9 chromium 2>/dev/null || true
pkill -9 chromedriver 2>/dev/null || true
sleep 1

# Nettoyage des repertoires temporaires orphelins
rm -rf /tmp/tmp* 2>/dev/null || true

# Lance Xvfb sur l'ecran :99 (headed Chromium = fingerprint humain)
Xvfb :99 -screen 0 1280x720x24 &
XVFB_PID=$!

# Garde-fou : relance le script si crash
# On utilise exec pour que python devienne le process parent et recoive les signaux
while true; do
    python -u lostgard_voter.py
    echo "[watchdog] Script termine — redemarrage dans 10s..."
    # Nettoyage agressif des processus Chrome orphelins avant de relancer
    pkill -9 chromium 2>/dev/null || true
    pkill -9 chromedriver 2>/dev/null || true
    # Nettoyer aussi les tmpdirs Chromium orphelins
    rm -rf /tmp/tmp* 2>/dev/null || true
    sleep 10
done

kill $XVFB_PID 2>/dev/null || true
