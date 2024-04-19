import json
import subprocess
import random
import time
import pyautogui
import pygetwindow as gw
import sys

import requests

# Liste des pays pour la connexion VPN
countries = ['France', 'Belgium', 'Luxembourg', 'London', 'Netherlands', 'Frankfurt',
             'Switzerland', 'Liechtenstein', 'Milan', 'Monaco', 'Marseille', 'Andorra',
             'Barcelona', 'Madrid']

blacklist_path = 'blacklist.json'


def load_blacklist():
    """ Charge la liste noire des IP depuis un fichier JSON """
    try:
        with open(blacklist_path, 'r') as file:
            try:
                # Tente de charger le JSON
                return json.load(file)
            except json.JSONDecodeError:
                # Si le JSON est vide ou invalide, retourne une liste vide
                return []
    except FileNotFoundError:
        # Si le fichier n'existe pas, retourne une liste vide
        return []


def save_blacklist(blacklist):
    """ Enregistre la liste noire des IP dans un fichier JSON """
    with open(blacklist_path, 'w') as file:
        json.dump(blacklist, file)


def get_current_ip():
    session = requests.Session()  # Création d'une session
    while True:  # Boucle infinie pour continuer jusqu'à obtenir une IP valide
        try:
            # Utilisation de HTTPS
            # Attendre 1 seconde avant de faire une nouvelle requête
            time.sleep(1)
            response = session.get('https://httpbin.org/ip', timeout=10)
            ip = response.json().get('origin')
            if ip:
                print(f"Adresse IP récupérée avec succès : {ip}")
                return ip
            else:
                print("Aucune adresse IP reçue, nouvelle tentative...")
        except requests.exceptions.RequestException as e:
            print("Erreur lors de la connexion, nouvelle tentative...", str(e))

        time.sleep(5)  # Attendre 5 secondes avant de réessayer


def check_ip_blacklist(ip, blacklist):
    """ Vérifie si l'IP est dans la liste noire """
    return ip in blacklist


def add_ip_to_blacklist(ip, blacklist):
    """ Ajoute une IP à la liste noire """
    blacklist.append(ip)
    save_blacklist(blacklist)


def connect_vpn(country):
    """ Tente de se connecter à un serveur VPN dans le pays spécifié """
    import subprocess
    try:
        result = subprocess.run(
            ["nordvpn", "-c", "-g", country], check=True, capture_output=True, text=True)
        print(f"Connecté avec succès à {country}")
        print("Sortie:", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la connexion à {country}: {str(e)}")
        print("Erreur:", e.stderr)


def focus_nordvpn_window():
    """ Met en avant et maximise la fenêtre de l'application NordVPN """
    try:
        window = pyautogui.getWindowsWithTitle('NordVPN')[0]
        if window.isMinimized:
            window.restore()
        window.maximize()  # Maximise la fenêtre
        window.activate()  # Met la fenêtre au premier plan
        print("Fenêtre NordVPN mise en avant et maximisée.")
    except IndexError:
        print("Fenêtre NordVPN non trouvée.")
    except Exception as e:
        print(f"Erreur lors de la mise en avant de la fenêtre: {str(e)}")


def focus_minecraft():
    """ Met en avant et maximise la fenêtre de Minecraft si elle contient 'Minecraft' dans le titre. """
    try:
        # Affichage des titres pour débogage
        print("Fenêtres ouvertes:", [w.title for w in gw.getAllWindows()])

        # Récupérer toutes les fenêtres et filtrer celles dont le titre contient 'Minecraft'
        windows = gw.getWindowsWithTitle('Minecraft')
        if windows:
            # Prendre la première fenêtre qui contient 'Minecraft'
            window = windows[0]
            if window.isMinimized:
                window.restore()
            window.maximize()  # Maximise la fenêtre
            window.activate()  # Met la fenêtre au premier plan
            print("Fenêtre Minecraft mise en avant et maximisée.")
        else:
            print("Aucune fenêtre Minecraft trouvée avec le titre spécifié.")
    except Exception as e:
        print(
            f"Erreur lors de la mise en avant de la fenêtre Minecraft: {str(e)}")

# Utilisation de la fonction


def find_vpn_connection():
    """ Cherche une image spécifique à l'écran indiquant que le VPN est connecté, vérification répétée toutes les 2 secondes. """
    timeout = 60  # Durée maximale de la vérification en secondes
    start_time = time.time()
    focus_nordvpn_window()
    while time.time() - start_time < timeout:
        try:
            # Image qui indique une connexion réussie
            location = pyautogui.locateOnScreen(
                'images/nord_connect.png', confidence=0.5)
            if location:
                print("Le VPN est maintenant pleinement opérationnel.")
                return True
        except pyautogui.ImageNotFoundException:
            print("Image non trouvée, continuez à vérifier...")
        except Exception as e:
            print(f"Erreur lors de la vérification de l'image: {str(e)}")

        print("VPN non connecté, nouvelle vérification dans 2 secondes...")
        time.sleep(2)  # Attente de 2 secondes avant de réessayer

    print("Délai de vérification dépassé sans confirmation de connexion VPN.")
    return False

  # Appel de la fonction pour vérifier et connecter le VPN


def check_and_connect():
    """ Tente de se connecter et vérifie la connexion par image """
    blacklist = load_blacklist()
    while True:
        selected_country = random.choice(countries)
        connect_vpn(selected_country)
        if find_vpn_connection():
            current_ip = get_current_ip()
            if check_ip_blacklist(current_ip, blacklist):
                print(
                    f"Adresse IP {current_ip} est dans la blacklist, reconnexion nécessaire...")
                continue
            add_ip_to_blacklist(current_ip, blacklist)

            print(
                f"Le VPN est maintenant pleinement opérationnel avec l'IP {current_ip}.")
            focus_minecraft()
            break
        else:
            print("Tentative de reconnexion...")
        time.sleep(5)  # Attendre 5 secondes avant de réessayer


check_and_connect()
# Assurez-vous de gérer correctement la fermeture de la connexion VPN si nécessaire
# à la fin de votre script, selon les fonctions disponibles dans le module utilisé.
