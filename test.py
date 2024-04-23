import subprocess
import time
import pygetwindow as gw
import pyautogui
import json
import pyautogui
import time
import cv2
import json
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
region_recherche = (710, 500, 500, 250)

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
cliquer_sur_image_zones(
        chemin_image_thunder, 0.8, region_recherche)
time.sleep(2)
cliquer_sur_image_zones(
        chemin_image, 0.6, region_recherche)


