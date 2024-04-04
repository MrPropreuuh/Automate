import time
import pyautogui
import json
import os
from time import sleep

def charger_donnees():
    with open('donnees.json', 'r') as fichier:
        donnees = json.load(fichier)
    return donnees["comptes"]

def cliquer_sur_image(nom_image, attente_apres=0.3, attendre_confirmation=False, delai_avant_click=0.1):
    chemin_image = os.path.join(os.getcwd(), 'images1080', nom_image)
    position = None
    while position is None:
        position = pyautogui.locateCenterOnScreen(chemin_image, confidence=0.8)
        if position:
            pyautogui.moveTo(position, duration=0.1)  # Déplace la souris vers l'emplacement de l'image avec une petite animation
            sleep(delai_avant_click)  # Attend un peu avant de cliquer
            pyautogui.click()
            print(f"Image {nom_image} trouvée et cliquée.")
            sleep(attente_apres)
        elif not attendre_confirmation:
            print(f"Image {nom_image} non trouvée.")
            break
        sleep(0.5)  # Attend un peu avant de réessayer

def trouver_image(nom_image, timeout=1000):
    chemin_image = os.path.join(os.getcwd(), 'images1080', nom_image)  # Correction du chemin
    debut = time.time()
    trouve = False
    while (time.time() - debut) < timeout:
        position = pyautogui.locateCenterOnScreen(chemin_image, confidence=0.5)
        if position:
            print(f"Image {nom_image} trouvée.")
            trouve = True
            break
        sleep(0.2)  # Attendre un peu avant de réessayer
    if not trouve:
        print(f"Image {nom_image} non trouvée après {timeout} secondes.")
    return trouve

def main():
    comptes = charger_donnees()

    for compte in comptes:
        cliquer_sur_image("ajout_account_auto.png")
        sleep(0.1)  # Augmenté le délai
        cliquer_sur_image("blank.png")
        pyautogui.write(compte["username"])
        cliquer_sur_image("add_offline.png")
        trouver_image("confirm_button.png")

if __name__ == "__main__":
    main()
