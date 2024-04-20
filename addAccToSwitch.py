import time
import pyautogui
import json
import os
from time import sleep


def charger_donnees():
    with open('donnees.json', 'r') as fichier:
        donnees = json.load(fichier)
    return donnees["comptes"]


def cliquer_sur_image(nom_image, attente_apres=0.3, delai_avant_click=0.1, timeout=10):
    chemin_image = os.path.join(os.getcwd(), 'images1080', nom_image)
    debut = time.time()
    while True:
        position = pyautogui.locateCenterOnScreen(chemin_image, confidence=0.8)
        if position:
            # Animation du mouvement de la souris
            pyautogui.moveTo(position, duration=0.1)
            sleep(delai_avant_click)  # Délai avant de cliquer
            pyautogui.click()
            print(f"Image {nom_image} trouvée et cliquée.")
            sleep(attente_apres)
            break
        elif time.time() - debut > timeout:
            print(f"Image {nom_image} non trouvée après {timeout} secondes.")
            break
        sleep(0.5)  # Court délai avant de réessayer


def main():
    comptes = charger_donnees()

    for compte in comptes:
        cliquer_sur_image("ajout_account_auto.png")
        cliquer_sur_image("blank.png")
        pyautogui.write(compte["username"])
        cliquer_sur_image("add_offline.png")
        cliquer_sur_image("confirm_button.png")


if __name__ == "__main__":
    main()
