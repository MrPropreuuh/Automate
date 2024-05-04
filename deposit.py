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

day2 = os.path.join(os.getcwd(), 'disposedaily', "day2.png")
day3 = os.path.join(os.getcwd(), 'disposedaily', "day3.png")
chemin_image = os.path.join(os.getcwd(), 'images1080', "rarecandy.png")
region_recherche = (710, 500, 500, 250)


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
        pyautogui.moveTo(emplacement)
        time.sleep(1)
        pyautogui.click(emplacement)

        # Relâcher la touche Shift avec pynput
        keyboard_controller.release(Key.shift)
        print(
            f"Image trouvée à l'emplacement {emplacement}, un clic a été effectué.")
    else:
        print("Image non trouvée.")


def verifier_presence_image(image_path, seuil=0.9):
    """
    Vérifie si une image est présente sur l'écran.

    :param image_path: Chemin vers l'image à rechercher.
    :param seuil: Seuil de correspondance pour la recherche d'images, par défaut à 0.9.
    :return: Le point central de l'image si trouvée, None sinon.
    """
    try:
        # Utilise locateCenterOnScreen pour trouver le centre de l'image sur l'écran
        position = pyautogui.locateCenterOnScreen(image_path, confidence=seuil)
        if position:
            print(f"Image trouvée à l'emplacement {position}.")
            return position
        else:
            print("Image non trouvée.")
            return None
    except Exception as e:
        print(
            f"Une erreur est survenue lors de la recherche de l'image : {str(e)}")
        return None


# Exemple d'utilisation de la fonction
image_chemin = 'images1080/tp.png'
resultat = verifier_presence_image(image_chemin)


def main():
    print(
        "Demande d'envoie accepter.")
    pyautogui.sleep(
        2)
    keyboard_controller.press(
        Key.enter)
    keyboard_controller.release(
        Key.enter)
    pyautogui.sleep(
        1)
    pyautogui.write(
        '/home rarecandy')
    time.sleep(
        1)
    keyboard_controller.press(
        Key.enter)
    keyboard_controller.release(
        Key.enter)
    pyautogui.sleep(
        12)
    if verifier_presence_image(chemin_image):
        print("Image trouvée, aucune action nécessaire.")
    else:
        print("Image non trouvée, action alternative en cours.")
        time.sleep(60)  # Attend 60 secondes avant de continuer
        # Simule la pression de la touche Enter
        keyboard_controller.press(Key.enter)
        keyboard_controller.release(Key.enter)  # Relâche la touche Enter
        pyautogui.sleep(1)  # Pause d'une seconde
        pyautogui.write('/home rarecandy')  # Écrit la commande
        time.sleep(1)  # Attend une seconde avant de continuer
        # Simule de nouveau la pression de la touche Enter
        keyboard_controller.press(Key.enter)
        keyboard_controller.release(Key.enter)  # Relâche la touche Enter
        pyautogui.sleep(
            15)
    mouse.click(
        Button.right, 1)
    pyautogui.sleep(1)
    pyautogui.moveTo(100, 100, duration=1)
    pyautogui.click
    pyautogui.sleep(1)
    cliquer_sur_image_zones(
        chemin_image, 0.6, region_recherche)
    cliquer_sur_image_zones(
        day2, 0.6, region_recherche)
    cliquer_sur_image_zones(
        day3, 0.6, region_recherche)
    keyboard_controller.press(
        Key.esc)
    keyboard_controller.release(
        Key.esc)


if __name__ == "__main__":
    main()
