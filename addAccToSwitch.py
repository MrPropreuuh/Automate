import pyautogui
import json
import os
from time import sleep

# Chargement des données des comptes depuis le fichier JSON


def charger_donnees():
    with open('donnees.json', 'r') as fichier:
        donnees = json.load(fichier)
    return donnees["comptes"]

# Fonction pour trouver et cliquer sur une image à l'écran


def cliquer_sur_image(nom_image, attente_apres=0.3, attendre_confirmation=False):
    chemin_image = os.path.join(os.getcwd(), 'images', nom_image)
    position = None
    while position is None:
        position = pyautogui.locateCenterOnScreen(chemin_image, confidence=0.8)
        if position:
            pyautogui.click(position)
            print(f"Image {nom_image} trouvée et cliquée.")
            sleep(attente_apres)
        elif not attendre_confirmation:
            print(f"Image {nom_image} non trouvée.")
            break
        sleep(0.5)  # Attendre un peu avant de réessayer

# Fonction pour attendre la confirmation avant de continuer


def attendre_confirmation(nom_image):
    print("En attente de la confirmation...")
    cliquer_sur_image(nom_image, attente_apres=0.3, attendre_confirmation=True)

# Main script


def main():
    comptes = charger_donnees()

    for compte in comptes:
        # Cliquer sur "ajout_account_auto.png"
        cliquer_sur_image("ajout_account_auto.png")

        # Cliquer sur "blank.png" pour sélectionner le champ du pseudo
        cliquer_sur_image("blank.png")

        # Écrire le nom d'utilisateur
        pyautogui.write(compte["username"])
        sleep(0.1)

        # Cliquer sur "add_offline.png" pour ajouter le compte
        cliquer_sur_image("add_offline.png")

        # Attendre la confirmation avant de passer au prochain compte
        attendre_confirmation("confirm_button.png")


if __name__ == "__main__":
    main()
