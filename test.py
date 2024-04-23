import time
import pygetwindow as gw
import pyautogui
import cv2
import json
import numpy as np
from mss import mss
import os
import datetime
import keyboard
import subprocess
from pynput.keyboard import Key
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button
import sys

keyboard_controller = KeyboardController()
mouse = MouseController()



def lire_json():
    with open('donnees.json', 'r', encoding='utf-8') as fichier:
        return json.load(fichier)


def ecrire_json(data):
    with open('donnees.json', 'w', encoding='utf-8') as fichier:
        json.dump(data, fichier, indent=4)


def cliquer_sur_image_daily(daily):
    dossier_images = "dailysreward/"
    nom_fichier = f"{dossier_images}day{daily}.png"
    position = pyautogui.locateCenterOnScreen(nom_fichier, confidence=0.8)
    if position:
        pyautogui.click(position)
        print(f"Image {nom_fichier} trouvée et cliquée.")
        return True
    return False

chemin_image = os.path.join(os.getcwd(), 'images1080', "rarecandy.png")


def cliquer_sur_image_zones(image_path, seuil=0.6, region=None):
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
        # Maintenir la touche Shift avec pynput
        keyboard_controller.press(Key.shift)

        # Réaliser un clic de souris à l'emplacement spécifié
        pyautogui.click(emplacement)

        # Relâcher la touche Shift avec pynput
        keyboard_controller.release(Key.shift)
        print(
            f"Image trouvée à l'emplacement {emplacement}, un clic a été effectué.")
    else:
        print("Image non trouvée.")

def deplacer_souris_aux_quatre_coins(region):
    """
    Déplace la souris aux quatre coins de la région spécifiée.

    :param region: Tuple de la région à utiliser (x, y, largeur, hauteur).
    """
    x, y, largeur, hauteur = region

    # Coin supérieur gauche
    pyautogui.moveTo(x, y)
    print(f"Souris déplacée au coin supérieur gauche: ({x}, {y})")
    time.sleep(1)  # Pause pour visualiser le mouvement

    # Coin supérieur droit
    pyautogui.moveTo(x + largeur, y)
    print(f"Souris déplacée au coin supérieur droit: ({x + largeur}, {y})")
    time.sleep(1)

    # Coin inférieur droit
    pyautogui.moveTo(x + largeur, y + hauteur)
    print(f"Souris déplacée au coin inférieur droit: ({x + largeur}, {y + hauteur})")
    time.sleep(1)

    # Coin inférieur gauche
    pyautogui.moveTo(x, y + hauteur)
    print(f"Souris déplacée au coin inférieur gauche: ({x}, {y + hauteur})")
    time.sleep(1)

# Exemple d'utilisation:
region_recherche = (710, 500, 500, 250)
# deplacer_souris_aux_quatre_coins(region_recherche)

time.sleep(2)
cliquer_sur_image_zones(chemin_image, 0.6, region_recherche)

