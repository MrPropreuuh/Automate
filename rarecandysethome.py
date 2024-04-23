import subprocess
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
from pynput.keyboard import Key
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button

keyboard_controller = KeyboardController()
mouse = MouseController()


def charger_donnees():
    with open('donnees.json', 'r') as fichier:
        donnees = json.load(fichier)
    return donnees


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
            compte["deposit"] = "true"
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
        if "Minecraft*" in titre:
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


def daily_reward(donnees):
    donnees = lire_json()
    mise_a_jour = False
    for compte in donnees["comptes"]:
        if compte['deposit'] == "false":
                compte['deposit'] = "true"
                mise_a_jour = True
                break  # Arrête après le premier clic réussi
    if mise_a_jour:
        # Sauvegarde les modifications dans le fichier JSON
        ecrire_json(donnees)

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


def attendre_image(image_path, seuil=0.8, temps_attente_max=30, intervalle=0.5):
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
        # Simuler la pression de la touche Enter, envoyer la commande, et relâcher la touche
        keyboard_controller.press(Key.enter)
        keyboard_controller.release(Key.enter)
        time.sleep(1)
        pyautogui.write('/tpa Uruma')
        keyboard_controller.press(Key.enter)
        keyboard_controller.release(Key.enter)

chemin_image = os.path.join(os.getcwd(), 'images1080', "rarecandy.png")
chemin_image_thunder = os.path.join(os.getcwd(), 'images1080', "thunder.png")
region_recherche = (710, 500, 500, 250)  # La région où chercher l'image


def cliquer_sur_image_zones(image_path, seuil=0.8, region=None):
    """
    Cherche une image dans une région spécifiée de l'écran et clique dessus si elle est trouvée.

    :param image_path: Chemin vers l'image à rechercher.
    :param seuil: Seuil de correspondance pour la recherche d'images.
    :param region: Tuple de la région à rechercher (x, y, largeur, hauteur).
    """
    try:
        # Tente de localiser l'image sur l'écran dans la région spécifiée
        emplacement = pyautogui.locateCenterOnScreen(
            image_path, confidence=seuil, region=region)

        # Si l'image est trouvée, effectuer un clic
        if emplacement:
            # Maintenir la touche Shift
            keyboard_controller.press(Key.shift)
            time.sleep(0.4)
            # Réaliser un clic de souris à l'emplacement spécifié
            pyautogui.moveTo(emplacement)
            time.sleep(0.4)

            pyautogui.click(emplacement)
            time.sleep(0.4)
            # Relâcher la touche Shift
            keyboard_controller.release(Key.shift)
            time.sleep(0.4)
            print(
                f"Image trouvée à l'emplacement {emplacement}, un clic a été effectué.")
        else:
            # Continue simplement sans interrompre le script
            print("Image non trouvée, continuation du script.")

    except Exception as e:
        # Gérer l'exception si nécessaire (optionnel)
        print(f"Une erreur s'est produite: {e}")


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


def main():
    donnees = charger_donnees()
    if fenetre_minecraft_ouverte():
        print("Minecraft 1.16.5 est ouvert. Recherche du menu principal...")
        # Spécifier un seuil pour la reconnaissance de l'image "menu.png"
        if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "menu.png"), 0.5):
            print("Menu Minecraft détecté. Début du script...")
            pyautogui.sleep(2)

            for compte in donnees["comptes"][:50]:
                if compte["deposit"] == "true":
                    print(
                        f"{compte['username']} a déja été checker.")
                    continue  # Passe au prochain compte
                id_compte = compte["id"]
                mdp = compte['motDePasse']
                pyautogui.sleep(1)
                # Spécifier un seuil différent pour la reconnaissance de l'image "acc_switch.png"
                if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "acc_switch.png"), 0.8):
                    print(
                        f"Changement de compte pour {compte['username']}.")
                    pyautogui.sleep(1)
                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "search_acc.png"), 0.8):
                        pyautogui.write(compte['username'])
                        pyautogui.sleep(1)
                    # Et encore un autre seuil pour "log_switch_acc.png"
                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "log_switch_acc.png"), 0.9):
                        print(f"Connecté avec {compte['username']}.")
                        pyautogui.sleep(0.5)
                        # Appuyer sur espace pour retourner au menu principal
                        if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "cancel.png"), 0.5):
                            # Attendre un peu que le menu principal s'affiche
                            pyautogui.sleep(1)
                            # Vérifiez que vous êtes bien de retour dans le menu principal
                            if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "menu.png"), 0.5):
                                print("Retour au menu principal confirmé.")
                                pyautogui.sleep(1)
                                # Cliquer sur l'image "multiplayer.png" pour accéder au menu multijoueur
                                if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "multiplayer.png"), 0.8):
                                    print("Accès au menu multijoueur.")
                                    pyautogui.sleep(1)

                                    # CHANGEMENT D'IP
                                    print("Changement d'IP en cours...")
                                    run_ip_changer()

                                    attendre_image(os.path.join(
                                        os.getcwd(), 'images1080', "verification_multiplayer.png"), 0.8)
                                    print("Retour au multiplayer.")
                                    pyautogui.sleep(2)
                                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "direct_conn.png"), 0.8):
                                        print(
                                            "Appuie sur Direct join.")
                                        pyautogui.sleep(1)
                                        if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "join.png"), 0.8):
                                            print(
                                                "Rejoindre le serveur.")
                                            pyautogui.sleep(3)
                                            attendre_image(os.path.join(
                                                os.getcwd(), 'images1080', "logging_acc.png"), 0.8)
                                            # Après l'enregistrement, ou d  irectement si on est sur la page de connexion
                                            if image_detectee(os.path.join(os.getcwd(), 'images1080', "logging_acc.png"), 0.8):
                                                pyautogui.sleep(3)
                                                print(
                                                    "Page de connexion détectée.")
                                                keyboard_controller.press(
                                                    Key.enter)
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
                                                    os.getcwd(), 'images1080', "join_pixelmon.png"), 0.8)
                                                if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "join_pixelmon.png"), 0.8):
                                                    print(
                                                        "Monde Pixelmon détecté.")
                                                    pyautogui.sleep(
                                                        15)
                                                    # Demande de téléportation en boucle
                                                    envoyer_tpa_et_verifier_image()
                                                    print(
                                                        "Demande d'envoie accepter.")
                                                    pyautogui.sleep(
                                                        15)
                                                    keyboard_controller.press(
                                                        Key.enter)
                                                    keyboard_controller.release(
                                                        Key.enter)
                                                    pyautogui.sleep(
                                                        1)
                                                    pyautogui.write(
                                                        '/sethome rarecandy')
                                                    keyboard_controller.press(
                                                        Key.enter)
                                                    keyboard_controller.release(
                                                        Key.enter)
                                                    pyautogui.sleep(
                                                        1)
                                                    keyboard_controller.press(
                                                        Key.enter)
                                                    keyboard_controller.release(
                                                        Key.enter)
                                                    pyautogui.sleep(
                                                        1)
                                                    pyautogui.write(
                                                        '/kit aventurier')
                                                    keyboard_controller.press(
                                                        Key.enter)
                                                    keyboard_controller.release(
                                                        Key.enter)
                                                    
                                                    pyautogui.sleep(
                                                        3)
                                                    mouse.click(
                                                        Button.right, 1)
                                                    pyautogui.sleep(1)
                                                    pyautogui.moveTo(100, 100, 0.2)
                                                    cliquer_sur_image_zones(
                                                        chemin_image, 0.5, region_recherche)
                                                    pyautogui.moveTo(100, 100, 0.2)
                                                    cliquer_sur_image_zones(
                                                        chemin_image_thunder, 0.8, region_recherche)
                                                    daily_reward(donnees)
                                                    time.sleep(1)
                                                    keyboard_controller.press(
                                                        Key.esc)
                                                    keyboard_controller.release(
                                                        Key.esc)
                                                    time.sleep(1)
                                                    keyboard_controller.press(
                                                        Key.esc)
                                                    keyboard_controller.release(
                                                        Key.esc)
                                                    attendre_image(os.path.join(
                                                        os.getcwd(), 'images1080', "disconnect.png"), 0.8)
                                                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images1080', "disconnect.png"), 0.8):
                                                        print(
                                                            "Déconnexion.")
                                                        pyautogui.sleep(
                                                            3)
                                                        cliquer_sur_image(os.path.join(
                                                            os.getcwd(), 'images1080', "cancel.png"), 0.8)
                                                    print(
                                                        "Retour au menu.")
                                                    pyautogui.sleep(
                                                        1)

                                            else:
                                                print(
                                                    "Pas de connexion au serveur ou inlisible.")
                                        else:
                                            print(
                                                "Bouton join non détecté.")
                                    else:
                                        print(
                                            "Bouton Direct join non détecté.")
                                else:
                                    print(
                                        "Le bouton multijoueur n'a pas été trouvé.")
                            else:
                                print(
                                    "Retour au menu principal non détecté. Vérification échouée.")
                        else:
                            print("Impossible de trouver le bouton de connexion.")
                        pyautogui.sleep(1)
                    else:
                        print("Le bouton de changement de compte n'a pas été trouvé.")
                    pyautogui.sleep(1)
        else:
            print("Vous n'êtes pas dans le menu Minecraft principal. Fin du script.")
    else:
        print("Minecraft 1.16.5 n'est pas ouvert.")


# Associez la touche "P" à la fonction toggle_macro
keyboard.add_hotkey('p', toggle_macro)
keyboard.add_hotkey('o', stop_macro)

print("Pressez 'P' pour démarrer/arrêter la macro.")
# Utilisez une touche (par exemple, 'esc') pour quitter le script
keyboard.wait('esc')
