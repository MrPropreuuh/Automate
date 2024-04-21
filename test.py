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
        pyautogui.click(emplacement)
        print(
            f"Image trouvée à l'emplacement {emplacement}, un clic a été effectué.")
    else:
        print("Image non trouvée.")


def deplacer_souris_autour_zone(region):
    """
    Déplace la souris autour des coins d'une région donnée.

    :param region: Tuple contenant les coordonnées de la région (x, y, largeur, hauteur).
    """
    x, y, largeur, hauteur = region

    # Calculer les coins de la région
    coin_haut_gauche = (x, y)
    coin_haut_droit = (x + largeur, y)
    coin_bas_gauche = (x, y + hauteur)
    coin_bas_droit = (x + largeur, y + hauteur)

    # Liste des coins à visiter
    coins = [coin_haut_gauche, coin_haut_droit,
             coin_bas_droit, coin_bas_gauche]

    # Boucle pour déplacer la souris à chaque coin
    for coin in coins:
        pyautogui.moveTo(coin)
        print(f"Souris déplacée à {coin}")
        time.sleep(0.5)  # Attendre 2 secondes à chaque coin


chemin_image = os.path.join(os.getcwd(), 'images1080', "rarecandy.png")
region_recherche = (1000, 700, 500, 250)  # La région où chercher l'image

# Passez la région de recherche en tant que paramètre à la fonction
deplacer_souris_autour_zone(region_recherche)
