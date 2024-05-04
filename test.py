import subprocess
import time
import pyautogui
import json
import cv2
import numpy as np
from mss import mss
import os
import datetime
import keyboard
from pynput.keyboard import Key
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button
import threading

keyboard_controller = KeyboardController()
mouse = MouseController()

chemin_image_thunder = "images1080/thunder.png"
region_recherche = (700, 570, 550, 300)  # (x, y, largeur, hauteur)

def deplacer_souris_aux_quatre_coins(region):
    """
    Déplace la souris aux quatre coins de la région spécifiée.
    
    :param region: Tuple de la région (x, y, largeur, hauteur).
    """
    x, y, largeur, hauteur = region
    coins = [
        (x, y),  # Coin supérieur gauche
        (x + largeur, y),  # Coin supérieur droit
        (x, y + hauteur),  # Coin inférieur gauche
        (x + largeur, y + hauteur)  # Coin inférieur droit
    ]
    for coin in coins:
        mouse.position = coin
        time.sleep(0.5)  # Pause pour visualiser le déplacement

def cliquer_sur_image_zones(image_path, seuil=0.8, region=None):
    """
    Cherche une image dans une région spécifiée de l'écran et clique dessus si elle est trouvée.

    :param image_path: Chemin vers l'image à rechercher.
    :param seuil: Seuil de correspondance pour la recherche d'images.
    :param region: Tuple de la région à rechercher (x, y, largeur, hauteur).
    """
    # Déplacer la souris aux quatre coins de la région pour s'assurer que la zone est visible
    deplacer_souris_aux_quatre_coins(region)
    
    # Tente de localiser l'image sur l'écran dans la région spécifiée
    emplacement = pyautogui.locateCenterOnScreen(
        image_path, confidence=seuil, region=region)

    # Si l'image est trouvée, effectuer un clic
    if emplacement:
        # Maintenir la touche Shift
        keyboard_controller.press(Key.shift)

        # Réaliser un clic de souris à l'emplacement spécifié
        pyautogui.click(emplacement)

        # Relâcher la touche Shift
        keyboard_controller.release(Key.shift)
        print(
            f"Image trouvée à l'emplacement {emplacement}, un clic a été effectué.")
    else:
        print("Image non trouvée.")

chemin_image = "images1080/rarecandy.png"
time.sleep(2)
deplacer_souris_aux_quatre_coins(region_recherche)
