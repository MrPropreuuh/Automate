import pyautogui
import webbrowser
import time
from PIL import Image


def find_and_click(image_path):
    """Cherche une image et clique dessus si elle est trouvée, sinon retourne False."""
    location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
    if location:
        pyautogui.click(location)
        print(f"{image_path} trouvée et cliquée à {location}")
        time.sleep(2)  # Pause avant de fermer la fenêtre
        pyautogui.hotkey('ctrl', 'w')  # Ferme la fenêtre active
        return True
    else:
        print(f"{image_path} non trouvée")
        return False


def attendre_image(image_path, check_interval=0.5):
    """Attend jusqu'à ce que l'image spécifiée apparaisse à l'écran."""
    while True:
        location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
        if location:
            print(f"Image {image_path} trouvée à {location}")
            return location
        time.sleep(check_interval)


def check_and_refresh(url, image_path1, image_path2, check_interval=5, refresh_interval=60):
    """Vérifie périodiquement les images et rafraîchit la page toutes les minutes dans une boucle infinie."""
    while True:  # Démarre la boucle infinie
        print("ATtente de l'images...")
        attendre_image(wait)  # Attend l'image initiale avant de commencer
        webbrowser.open(url)  # Ouvre l'URL spécifiée dans un navigateur
        time.sleep(60)  # Laisse le temps à la page de charger
        last_refresh_time = time.time()  # Initialise le dernier temps de rafraîchissement

        while True:  # Boucle interne pour vérifier et rafraîchir la page
            if find_and_click(image_path1) or find_and_click(image_path2):
                print("Opération terminée avec succès.")
                time.sleep(2)  # Pause après l'action
                break  # Sortie de la boucle interne après l'action

            current_time = time.time()
            if current_time - last_refresh_time > refresh_interval:
                pyautogui.press('f5')  # Rafraîchit la page
                print("Page rafraîchie.")
                last_refresh_time = current_time

            time.sleep(check_interval)  # Pause entre les vérifications

        # Ferme le navigateur après avoir traité les images nécessaires
        image_path = 'site/confirm.png'
        attendre_image(image_path)
        pyautogui.hotkey('ctrl', 'w')


# Chemins vers les images à surveiller
wait = 'site/auto-vote.png'
image_path1 = 'site/vote1.png'
image_path2 = 'site/vote2.png'

# URL à ouvrir
url = 'https://pixelmongo.fr/vote'

# Lance la surveillance
check_and_refresh(url, image_path1, image_path2)
