import time
import pygetwindow as gw
import pyautogui
import cv2
import json
import numpy as np
from mss import mss
import os
import datetime


def charger_donnees():
    with open('donnees.json', 'r') as fichier:
        donnees = json.load(fichier)
    return donnees


def enregistrer_script_schedule(donnees):
    # Format de la date et de l'heure pour la réutilisation en Python
    date_heure_actuelle = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    donnees["scriptSchedule"] = {"date_heure": date_heure_actuelle}
    sauvegarder_donnees(donnees)
    print(f"Script Schedule enregistré pour {date_heure_actuelle}.")


def verifier_disponibilite_kit(donnees, compte):
    if "scriptSchedule" in donnees:
        dernier_run = datetime.datetime.strptime(
            donnees["scriptSchedule"]["date_heure"], "%Y-%m-%d %H:%M:%S")
        if (datetime.datetime.now() - dernier_run) < datetime.timedelta(hours=24):
            print(
                f"Le kit starter n'est toujours pas disponible. Relancer le script après {(dernier_run + datetime.timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')}")
            return False
        else:
            print("Kit disponible! Début de la récolte.")
            if compte["today"] == "true":
                compte["today"] = "false"
            return True
    else:
        print("Aucune programmation précédente trouvée. Début de la récolte.")
        return True


def fenetre_minecraft_ouverte():
    titres_fenetres = [w.title for w in gw.getAllWindows()]
    for titre in titres_fenetres:
        if "Minecraft 1.12.2" in titre:
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
        pyautogui.click(centre_x, centre_y)
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


donnees = charger_donnees()

if not verifier_disponibilite_kit(donnees):
    exit()

if fenetre_minecraft_ouverte():
    print("Minecraft 1.12.2 est ouvert. Recherche du menu principal...")
    # Spécifier un seuil pour la reconnaissance de l'image "menu.png"
    if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "menu.png"), 0.5):
        print("Menu Minecraft détecté. Début du script...")
        pyautogui.sleep(2)

        for compte in donnees["comptes"][:50]:
            if compte["today"] == "true":
                print(f"{compte['username']} a déjà fait son kit aujourd'hui.")
                continue  # Passe au prochain compte
            id_compte = compte["id"]
            pyautogui.sleep(1)
            # Spécifier un seuil différent pour la reconnaissance de l'image "acc_switch.png"
            if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "acc_switch.png"), 0.8):
                print(f"Changement de compte pour {compte['username']}.")
                pyautogui.sleep(1)
                if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "search_acc.png"), 0.8):
                    pyautogui.write(compte['username'])
                    pyautogui.sleep(1)
                # Et encore un autre seuil pour "log_switch_acc.png"
                if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "log_switch_acc.png"), 0.9):
                    print(f"Connecté avec {compte['username']}.")
                    pyautogui.sleep(0.5)
                    # Appuyer sur espace pour retourner au menu principal
                    pyautogui.press('escape')
                    # Attendre un peu que le menu principal s'affiche
                    pyautogui.sleep(1)
                    # Vérifiez que vous êtes bien de retour dans le menu principal
                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "menu.png"), 0.5):
                        print("Retour au menu principal confirmé.")
                        pyautogui.sleep(1)
                        # Cliquer sur l'image "multiplayer.png" pour accéder au menu multijoueur
                        if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "multiplayer.png"), 0.8):
                            print("Accès au menu multijoueur.")
                            pyautogui.sleep(1)

                            # Clique sur l'image proxy.png pour sélectionner le champ du proxy
                            if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "proxy.png"), 0.8):
                                print("Champ de proxy sélectionné.")
                                pyautogui.sleep(1)

                                # Appuyez et maintenez la touche 'ctrl'
                                pyautogui.keyDown('ctrl')
                                # Appuyez sur 'a' pendant que 'ctrl' est maintenu
                                pyautogui.press('a')
                                # Relâchez la touche 'ctrl'
                                pyautogui.keyUp('ctrl')
                                pyautogui.press('delete')
                                pyautogui.sleep(1)

                                # Pour chaque compte dans donnees.json
                                # Limite à 30 comptes

                                print(
                                    f"Configuration du proxy pour {compte['username']}.")

                                # Entrez le proxy et le port associé au compte actuel
                                proxy = f"{compte['proxy']}:{compte['port']}"
                                pyautogui.write(proxy)
                                mdp = compte['motDePasse']
                                pyautogui.sleep(1)

                                # Clique sur l'image test_proxy.png
                                if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "test_proxy.png"), 0.8):
                                    print("Test du proxy en cours...")
                                    # Donnez du temps pour le test du proxy
                                    pyautogui.sleep(3)

                                    # Clique sur l'image apply_proxy.png
                                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "apply_proxy.png"), 0.8):
                                        print("Application du proxy.")
                                        attendre_image(os.path.join(
                                            os.getcwd(), 'images', "verification_multiplayer.png"), 0.8)
                                        print("Retour au multiplayer.")
                                        pyautogui.sleep(2)
                                        if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "direct_conn.png"), 0.8):
                                            print(
                                                "Appuie sur Direct join.")
                                            pyautogui.sleep(1)
                                            if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "join.png"), 0.8):
                                                print(
                                                    "Rejoindre le serveur.")
                                                attendre_image(os.path.join(
                                                    os.getcwd(), 'images', "connected_server.png"), 0.8)
                                                pyautogui.sleep(3)
                                                # Vérification pour l'enregistrement ou la connexion
                                                if image_detectee(os.path.join(os.getcwd(), 'images', "register_acc.png"), 0.8):
                                                    print(
                                                        "Page d'enregistrement détectée.")
                                                    pyautogui.press(
                                                        'enter')
                                                    pyautogui.sleep(1)
                                                    pyautogui.write(
                                                        f'/register {mdp} {mdp}')
                                                    pyautogui.press(
                                                        'enter')
                                                    pyautogui.sleep(1)

                                                    pyautogui.press(
                                                        '1')
                                                    pyautogui.rightClick()
                                                    attendre_image(os.path.join(
                                                        os.getcwd(), 'images', "join_pixelmon.png"), 0.8)
                                                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "join_pixelmon.png"), 0.8):
                                                        print(
                                                            "Monde Pixelmon détecté.")
                                                        pyautogui.sleep(1)
                                                        attendre_image(os.path.join(
                                                            os.getcwd(), 'images', "select-starter-confirm.png"), 0.8)
                                                        if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "starter_pick.png"), 0.8):
                                                            print(
                                                                "Choix du starter détecté.")
                                                            pyautogui.sleep(
                                                                1)
                                                            if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "validate_starter.png"), 0.8):
                                                                print(
                                                                    "Validation du starter détectée.")
                                                                pyautogui.press(
                                                                    'enter')
                                                                pyautogui.sleep(
                                                                    1)
                                                                pyautogui.write(
                                                                    '/kit aventurier')
                                                                pyautogui.press(
                                                                    'enter')
                                                                pyautogui.sleep(
                                                                    1)
                                                                if image_detectee(os.path.join(os.getcwd(), 'images', "kit_valid.png"), 0.8):
                                                                    mettre_a_jour_status_si_kit_valid(
                                                                        donnees, compte)
                                                                    pyautogui.press(
                                                                        'escape')
                                                                    pyautogui.leftClick()
                                                                    print(
                                                                        "Déconnexion.")
                                                                    pyautogui.sleep(
                                                                        1)
                                                                    pyautogui.press(
                                                                        'escape')
                                                                if image_detectee(os.path.join(os.getcwd(), 'images', "kit_fail.png"), 0.8):
                                                                    mettre_a_jour_status_si_kit_false(
                                                                        donnees, compte)
                                                                    pyautogui.press(
                                                                        'escape')
                                                                    pyautogui.leftClick()
                                                                    print(
                                                                        "Déconnexion.")
                                                                    pyautogui.sleep(
                                                                        1)
                                                                    pyautogui.press(
                                                                        'escape')
                                                            else:
                                                                print(
                                                                    "Validation du starter non détectée.")
                                                        else:
                                                            print(
                                                                "Choix du starter non détecté.")
                                                    else:
                                                        print(
                                                            "Monde Pixelmon non détecté.")

                                                # Après l'enregistrement, ou d  irectement si on est sur la page de connexion
                                                if image_detectee(os.path.join(os.getcwd(), 'images', "logging_acc.png"), 0.8):
                                                    attendre_image(os.path.join(
                                                        os.getcwd(), 'images', "connected_server.png"), 0.8)
                                                    pyautogui.sleep(3)
                                                    print(
                                                        "Page de connexion détectée.")
                                                    pyautogui.press(
                                                        'enter')
                                                    pyautogui.sleep(1)
                                                    pyautogui.write(
                                                        f'/login {mdp}')
                                                    pyautogui.press(
                                                        'enter')
                                                    pyautogui.sleep(1)

                                                    pyautogui.press(
                                                        '1')
                                                    pyautogui.rightClick()
                                                    pyautogui.sleep(1)
                                                    attendre_image(os.path.join(
                                                        os.getcwd(), 'images', "join_pixelmon.png"), 0.8)
                                                    if cliquer_sur_image(os.path.join(os.getcwd(), 'images', "join_pixelmon.png"), 0.8):
                                                        print(
                                                            "Monde Pixelmon détecté.")
                                                        pyautogui.sleep(3)
                                                        pyautogui.press(
                                                            'enter')
                                                        pyautogui.sleep(
                                                            1)
                                                        pyautogui.write(
                                                            '/kit aventurier')
                                                        pyautogui.press(
                                                            'enter')
                                                        pyautogui.sleep(
                                                            1)
                                                        if image_detectee(os.path.join(os.getcwd(), 'images', "kit_valid.png"), 0.8):
                                                            mettre_a_jour_status_si_kit_valid(
                                                                donnees, compte)
                                                            pyautogui.press(
                                                                'escape')
                                                            pyautogui.leftClick()
                                                            print(
                                                                "Déconnexion.")
                                                            pyautogui.sleep(
                                                                1)
                                                            pyautogui.press(
                                                                'escape')
                                                        if image_detectee(os.path.join(os.getcwd(), 'images', "kit_fail.png"), 0.8):
                                                            mettre_a_jour_status_si_kit_false(
                                                                donnees, compte)
                                                            pyautogui.press(
                                                                'escape')
                                                            pyautogui.leftClick()
                                                            print(
                                                                "Déconnexion.")
                                                            pyautogui.sleep(
                                                                1)
                                                            pyautogui.press(
                                                                'escape')

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
                                            "Bouton cancel de proxy non détecté.")
                                else:
                                    print(
                                        "L'option de configuration du proxy n'a pas été trouvée.")
                            else:
                                print(
                                    "Vous n'êtes pas dans le menu multijoueur. Fin du script.")
                        else:
                            print("Le bouton multijoueur n'a pas été trouvé.")
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
    print("Minecraft 1.12.2 n'est pas ouvert.")
