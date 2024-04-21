import os
import time
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button
import pyautogui
from pynput.keyboard import Controller, Key

keyboard = Controller()
mouse = MouseController()


def cliquer_sur_image_zones(image_path, seuil=0.8, region=None):
    """
    Cherche une image dans une région spécifiée de l'écran et clique dessus si elle est trouvée.

    :param image_path: Chemin vers l'image à rechercher.
    :param seuil: Seuil de correspondance pour la recherche d'images.
    :param region: Tuple de la région à rechercher (x, y, largeur, hauteur).
    """
    # Tente de localiser l'image sur l'écran dans la région spécifiée
    emplacement = pyautogui.locateCenterOnScreen(
        image_path, confidence=seuil, region=region)

    # Si l'image est trouvée, effectuer un clic
    if emplacement:
        time.sleep(3)
        # Maintenir la touche Shift
        keyboard.press(Key.shift)

        # Réaliser un clic de souris à l'emplacement spécifié
        pyautogui.click(emplacement)

        # Relâcher la touche Shift
        keyboard.release(Key.shift)
        print(
            f"Image trouvée à l'emplacement {emplacement}, un clic a été effectué.")
    else:
        print("Image non trouvée.")


chemin_image = os.path.join(os.getcwd(), 'images1080', "rarecandy.png")
region_recherche = (1030, 700, 500, 250)  # La région où chercher l'image

# Passez la région de recherche en tant que paramètre à la fonction
cliquer_sur_image_zones(chemin_image, 0.8, region_recherche)
