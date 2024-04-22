import json
import pyautogui
import time


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


def daily_reward():
    data = lire_json()
    for compte in data['comptes']:
        if compte['id'] == 1:  # Vérifie si l'ID du compte est 1
            if compte['dailyComplete'] == "false":
                if cliquer_sur_image_daily(compte['daily']):
                    compte['dailyComplete'] = "true"
                    # Incrémente daily pour le prochain jour
                    compte['daily'] += 1
                    break  # Arrête après le premier clic réussi
    ecrire_json(data)


daily_reward()
