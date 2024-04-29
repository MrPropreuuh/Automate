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


def charger_donnees():
    with open('donnees.json', 'r') as fichier:
        donnees = json.load(fichier)
    return donnees


def lire_json():
    with open('donnees.json', 'r', encoding='utf-8') as fichier:
        return json.load(fichier)


def ecrire_json(data):
    with open('donnees.json', 'w', encoding='utf-8') as fichier:
        json.dump(data, fichier, indent=4)


def cliquer_sur_image_daily(daily):
    time.sleep(1)  # Attendre 1 seconde avant de cliquer sur l'image
    dossier_images = "dailysreward/"
    nom_fichier = f"{dossier_images}day{daily}.png"
    position = pyautogui.locateCenterOnScreen(nom_fichier, confidence=0.6)
    if position:
        time.sleep(2)
        pyautogui.moveTo(position)
        time.sleep(1)
        pyautogui.click(position)
        print(f"Image {nom_fichier} trouvée et cliquée.")
        return True
    return False


def focus_pixelmon_launcher():
    """
    Cette fonction recherche une fenêtre avec le titre 'PixelmonGo - Launcher' et la met en avant.
    Si la fenêtre est trouvée, elle est restaurée et maximisée.
    """
    try:
        # Trouver la fenêtre par son titre
        window = gw.getWindowsWithTitle('PixelmonGo')[0]
        if window.isMinimized:  # Vérifie si la fenêtre est minimisée
            window.restore()  # Restaurer la fenêtre si minimisée
        window.maximize()  # Maximiser la fenêtre
        window.activate()  # Mettre la fenêtre au premier plan
        print("Fenêtre 'PixelmonGo - Launcher' mise en avant et maximisée.")
    except IndexError:
        # Gérer le cas où la fenêtre n'est pas trouvée
        print("La fenêtre 'PixelmonGo - Launcher' n'a pas été trouvée.")
    except Exception as e:
        # Gérer d'autres exceptions potentielles
        print(
            f"Une erreur est survenue lors de la mise en avant de la fenêtre: {str(e)}")


def focus_minecraft_tab():
    """
    Cette fonction recherche une fenêtre avec le titre 'PixelmonGo - Launcher' et la met en avant.
    Si la fenêtre est trouvée, elle est restaurée et maximisée.
    """
    try:
        # Trouver la fenêtre par son titre
        window = gw.getWindowsWithTitle('Minecraft* 1.16.5')[0]
        if window.isMinimized:  # Vérifie si la fenêtre est minimisée
            window.restore()  # Restaurer la fenêtre si minimisée
        window.maximize()  # Maximiser la fenêtre
        window.activate()  # Mettre la fenêtre au premier plan
        print("Fenêtre 'PixelmonGo - Launcher' mise en avant et maximisée.")
    except IndexError:
        # Gérer le cas où la fenêtre n'est pas trouvée
        print("La fenêtre 'PixelmonGo - Launcher' n'a pas été trouvée.")
    except Exception as e:
        # Gérer d'autres exceptions potentielles
        print(
            f"Une erreur est survenue lors de la mise en avant de la fenêtre: {str(e)}")


def run_ip_changer():
    """Exécute le script ipchanger.py et attend que le processus se termine."""
    try:
        # Spécifiez le chemin complet si le script n'est pas dans le même dossier
        result = subprocess.run(
            ['python', 'ipchanger.py'], capture_output=True, text=True, check=True)
        print(f"ipchanger.py a terminé avec le résultat: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"ipchanger.py a échoué avec l'erreur: {e.stderr}")


def mettre_a_jour_status_check(donnees, compte_username):
    # Trouver le compte dans les données chargées
    for compte in donnees["comptes"]:
        if compte["username"] == compte_username:
            compte["ivsCheck"] = "true"
            break  # Sortie de la boucle une fois le compte trouvé et mis à jour

    # Sauvegarde des données mises à jour dans le fichier JSON
    sauvegarder_donnees(donnees, 'donnees.json')


def enregistrer_script_schedule(donnees):
    # Format de la date et de l'heure pour la réutilisation en Python
    date_heure_actuelle = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    donnees["scriptSchedule"] = {"date_heure": date_heure_actuelle}
    sauvegarder_donnees(donnees)
    print(f"Script Schedule enregistré pour {date_heure_actuelle}.")


def fenetre_minecraft_ouverte():
    titres_fenetres = [w.title for w in gw.getAllWindows()]
    for titre in titres_fenetres:
        if "PixelmonGo*" in titre:
            return True
    return False


def trouver_image(image_path):
    with mss() as sct:
        # Supposant que Minecraft est sur le premier moniteur
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        template = cv2.imread(image_path)
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        return max_val, max_loc, template.shape[::-1]


def sauvegarder_donnees(donnees, nom_fichier='donnees.json'):
    with open(nom_fichier, 'w') as fichier:
        json.dump(donnees, fichier, indent=4)


def cliquer_sur_image(image_path, seuil):
    max_val, max_loc, shape = trouver_image(image_path)
    if max_val > seuil:  # Utilisation du seuil spécifié
        # Calcul du centre de l'image détectée
        centre_x = max_loc[0] + shape[1] / 2
        centre_y = max_loc[1] + shape[0] / 2
        # Positionne la souris au centre de l'image détectée
        pyautogui.moveTo(centre_x, centre_y)
        # Attend 0.1 seconde
        time.sleep(0.1)
        # Clique à l'emplacement actuel de la souris
        pyautogui.click()
        return True
    return False


def attendre_image(image_path, seuil=0.8, temps_attente_max=300, intervalle=0.5):
    """
    Attends qu'une image soit détectée à l'écran.

    :param image_path: Chemin vers l'image à détecter.
    :param seuil: Seuil de détection pour considérer l'image comme trouvée.
    :param temps_attente_max: Temps maximum à attendre en secondes.
    :param intervalle: Intervalle entre les tentatives de détection en secondes.
    """
    debut = time.time()
    while True:
        max_val, max_loc, shape = trouver_image(image_path)
        if max_val > seuil:
            print(f"Image {image_path} détectée.")
            return True  # Image trouvée
        if time.time() - debut > temps_attente_max:
            print(f"Image {image_path} non détectée dans le délai imparti.")
            return False  # Dépassement du temps d'attente
        time.sleep(intervalle)


def image_detectee(image_path, seuil):
    max_val, _, _ = trouver_image(image_path)
    return max_val > seuil


def mettre_a_jour_status_si_kit_valid(donnees, compte):
    if compte["status"] == "error":
        compte["status"] = "success"
    if compte["today"] == "false":
        compte["today"] = "true"
        print(f"Compte {compte['username']} a un kit changement réussi.")
    if compte["id"] == 1:  # Vérifie si l'ID du compte est 1
        # Appel de la fonction pour enregistrer la date et l'heure
        enregistrer_script_schedule(donnees)
    sauvegarder_donnees(donnees)


def daily_reward(donnees):
    donnees = lire_json()
    mise_a_jour = False
    for compte in donnees["comptes"]:
        if compte['dailyComplete'] == "false":
            if cliquer_sur_image_daily(compte['daily']):
                compte['dailyComplete'] = "true"
                compte['daily'] += 1  # Incrémente daily pour le prochain jour
                mise_a_jour = True
                break  # Arrête après le premier clic réussi
    if mise_a_jour:
        # Sauvegarde les modifications dans le fichier JSON
        ecrire_json(donnees)


def mettre_a_jour_status_si_kit_false(donnees, compte):
    if compte["status"] == "success":
        compte["status"] = "error"
    if compte["today"] == "false":
        compte["today"] = "true"
        print(f"Compte {compte['username']} n'a pas de kit changement réussi.")
    if compte["id"] == 1:  # Vérifie si l'ID du compte est 1
        # Appel de la fonction pour enregistrer la date et l'heure
        enregistrer_script_schedule(donnees)
    sauvegarder_donnees(donnees)


def verifier_et_attendre_image(image_path, seuil=0.8, intervalle=1, temps_attente_max=60):
    debut = time.time()
    while time.time() - debut < temps_attente_max:
        # Insérer ici le code pour vérifier la présence de l'image
        # Si l'image est détectée, retournez True
        if False:  # Remplacer False par la condition réelle de détection de l'image
            print(f"Image {image_path} détectée.")
            return True
        time.sleep(intervalle)  # Attendez une seconde avant de réessayer
    print(f"Image {image_path} non détectée après {temps_attente_max} secondes.")
    return False


def envoyer_tpa_et_verifier_image():
    while True:
        # Simuler la pression de la touche Enter, envoyer la commande, et relâcher la touche
        keyboard_controller.press('t')
        keyboard_controller.release('t')
        time.sleep(1)
        pyautogui.write('/tpa Uruma')
        keyboard_controller.press('t')
        keyboard_controller.release('t')

        # Vérifie si l'image est trouvée avec l'intervalle spécifié
        image_trouvee = verifier_et_attendre_image(
            os.path.join(os.getcwd(), 'images1080', "accept.png"))

        # Si l'image est trouvée, arrêtez la boucle
        if image_trouvee:
            break

        # Attendez une minute avant de réessayer
        time.sleep(60)


chemin_image = os.path.join(os.getcwd(), 'images1080', "rarecandy.png")
region_recherche = (710, 500, 500, 250)  # VERSION PROTABLE
region_recherche_bureau = (1030, 690, 500, 250)  #


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
        keyboard.press(Key.shift)

        # Réaliser un clic de souris à l'emplacement spécifié
        pyautogui.click(emplacement)

        # Relâcher la touche Shift
        keyboard.release(Key.shift)
        print(
            f"Image trouvée à l'emplacement {emplacement}, un clic a été effectué.")
    else:
        print("Image non trouvée.")


macro_active = False


def stop_macro():
    global macro_active
    macro_active = False
    print("Arrêt de la macro...")


def toggle_macro():
    global macro_active
    macro_active = not macro_active  # Basculez l'état de macro_active
    if macro_active:
        print("Macro activée.")
        main()  # Démarrez votre macro
    else:
        print("Macro désactivée.")
        # Ici, vous pouvez ajouter un code pour arrêter proprement votre macro si nécessaire


def cliquer_a_un_point(x, y):
    """Déplace le curseur à la position (x, y) et effectue un clic gauche."""
    mouse.position = (x, y)  # Définit la position du curseur
    mouse.click(Button.left)  # Effectue un clic gauche


def main():
    donnees = charger_donnees()
    print("Minecraft 1.16.5 est ouvert. Recherche du menu principal...")
    # Spécifier un seuil pour la reconnaissance de l'image "menu.png"
    print("Menu Minecraft détecté. Début du script...")

    for compte in donnees["comptes"][:100]:
        if compte["dailyComplete"] == "true":
            print(
                f"{compte['username']} a déja été checker.")
            continue  # Passe au prochain compte
        id_compte = compte["id"]
        mdp = compte['motDePasse']
        pyautogui.sleep(1)
        run_ip_changer()
        focus_pixelmon_launcher()
        # Spécifier un seuil différent pour la reconnaissance de l'image "acc_switch.png"
        attendre_image(os.path.join(
            os.getcwd(), 'dailysreward', "luncher.png"), 0.8)
        if cliquer_sur_image(os.path.join(os.getcwd(), 'dailysreward', "luncher.png"), 0.8):

            # cliquer_a_un_point(600, 560)  # VERSION PORTABLE
            cliquer_a_un_point(700, 750)  # VERSION BUREAU

            pyautogui.sleep(1)
            # Appuyer sur Ctrl + Suppr
            keyboard_controller.press(Key.ctrl)
            keyboard_controller.press("a")
            time.sleep(0.1)
            # Relâcher Ctrl + Suppr
            keyboard_controller.release("a")
            keyboard_controller.release(Key.ctrl)
            keyboard_controller.press(Key.delete)
            time.sleep(0.1)

            pyautogui.write(compte['username'])
            cliquer_sur_image(os.path.join(
                os.getcwd(), 'dailysreward', "play.png"), 0.8)
            pyautogui.sleep(40)
            focus_minecraft_tab()
            attendre_image(os.path.join(
                os.getcwd(), 'images1080', "logging_acc.png"), 0.8)
            # Après l'enregistrement, ou d  irectement si on est sur la page de connexion
            if image_detectee(os.path.join(os.getcwd(), 'images1080', "logging_acc.png"), 0.8):
                pyautogui.sleep(3)
                print(
                    "Page de connexion détectée.")
                keyboard_controller.press(
                    't')
                pyautogui.sleep(1)
                pyautogui.write(
                    f'/login {mdp}')
                keyboard_controller.press(
                    Key.enter)
                pyautogui.sleep(1)

                keyboard_controller.press('1')
                keyboard_controller.release(
                    '1')
                pyautogui.sleep(1)
                mouse.click(Button.right, 1)
                attendre_image(os.path.join(
                    os.getcwd(), 'dailysreward', "join.png"), 0.8)
                if cliquer_sur_image(os.path.join(os.getcwd(), 'dailysreward', "join.png"), 0.8):
                    print(
                        "Monde Pixelmon détecté.")
                    time.sleep(10)
                    keyboard_controller.press(
                        't')
                    pyautogui.sleep(1)
                    pyautogui.write(
                        f'/dailyreward')
                    keyboard_controller.press(
                        Key.enter)
                    pyautogui.sleep(1)
                    daily_reward(donnees)
                    time.sleep(3)
                    keyboard_controller.press(Key.esc)
                    time.sleep(3)
                    cliquer_sur_image(os.path.join(
                        os.getcwd(), 'dailysreward', "disconnect.png"), 0.8)
                    time.sleep(3)
                    keyboard_controller.press(Key.alt)
                    keyboard_controller.press(Key.f4)

                    # Relâcher Alt + F4
                    keyboard_controller.release(Key.f4)
                    keyboard_controller.release(Key.alt)

                    time.sleep(5)
                    focus_pixelmon_launcher()


# Associez la touche "P" à la fonction toggle_macro
keyboard.add_hotkey('p', toggle_macro)
keyboard.add_hotkey('o', stop_macro)

print("Pressez 'P' pour démarrer/arrêter la macro.")
# Utilisez une touche (par exemple, 'esc') pour quitter le script
keyboard.wait('esc')
