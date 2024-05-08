import pyautogui
import time
import keyboard


def click_right(x, y):
    """ Effectue un clic droit à une position donnée """
    pyautogui.rightClick(x, y)


def find_image_with_timeout_and_click(image_path, timeout, action='left'):
    """ Tente de trouver et de cliquer sur une image sur l'écran pendant un délai défini (timeout en secondes). """
    start_time = time.time()
    while time.time() - start_time < timeout:
        location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
        if location:
            if action == 'left':
                pyautogui.click(location.x, location.y)
            elif action == 'right':
                pyautogui.rightClick(location.x, location.y)
            return True
    return False


def emergency_commands():
    """ Exécute une série de commandes de secours. """
    keyboard.press_and_release('enter')
    time.sleep(1)
    keyboard.write('/endbattle')
    time.sleep(1)
    keyboard.press_and_release('enter')
    pyautogui.leftClick()
    keyboard.press_and_release('enter')
    time.sleep(1)
    keyboard.write('/t spawn')
    time.sleep(1)
    keyboard.press_and_release('enter')
    time.sleep(15)
    keyboard.press_and_release('2')
    pyautogui.rightClick()
    time.sleep(8)
    keyboard.press_and_release('enter')
    time.sleep(1)
    keyboard.write('/home fish')
    time.sleep(1)
    keyboard.press_and_release('enter')
    time.sleep(15)
    keyboard.press_and_release('1')
    time.sleep(1)
    pyautogui.rightClick()
    print("Commande de secours exécutée, reprise de la surveillance...")


def find_and_click(image_path, action='left'):
    """ Trouve et clique sur une image donnée, retourne True si trouvée """
    location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
    if location:
        if action == 'left':
            pyautogui.click(location.x, location.y)
        elif action == 'right':
            pyautogui.rightClick(location.x, location.y)
        return True
    return False


def monitor_image_until_found(image_path, timeout=30):
    """Surveille une image jusqu'à ce qu'elle soit trouvée ou jusqu'à ce que le temps imparti soit écoulé, retourne les coordonnées ou effectue un clic droit."""
    start_time = time.time()  # Démarre le compteur de temps

    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        location = pyautogui.locateOnScreen(image_path, confidence=0.88)
        if location:
            return location  # Image trouvée, retourne la localisation

        if elapsed_time > timeout:
            print("Image non trouvée dans le temps imparti de 15 secondes.")
            # Effectue un clic droit si l'image n'est pas trouvée dans les 15 secondes
            pyautogui.rightClick()
            return None  # Retourne None pour indiquer que l'image n'a pas été trouvée


def main_routine_with_logs():
    while True:
        # Étape 1: Surveiller fish.png
        print("Surveillance de fish.png...")
        fish_location = monitor_image_until_found("fish/fish.png")
        print("fish.png trouvé à:", fish_location)
        if fish_location is None:
            print(
                "fish.png non trouvé dans le temps imparti. Exécution des commandes de secours...")  # Exécuter les commandes de secours si fish.png n'est pas trouvé
            continue  # Revenir au début de la boucle pour re-tenter la détection

        # Étape 2: Clic droit là où fish.png a été trouvé
        click_right(fish_location.left, fish_location.top)
        time.sleep(1)  # Petite pause pour laisser le clic droit se terminer
        print("Clic droit effectué à la position de fish.png")

        # Étape 3: Vérifier la présence de battle.png
        print("Recherche de battle.png...")

        found = pyautogui.locateOnScreen("fish/battle.png", confidence=0.9)
        if not found:
            print("battle.png non trouvé, attente et réessayer...")
            time.sleep(1)  # Attente d'une seconde
            # Réaliser à nouveau un clic droit là où fish.png a été trouvé
            pyautogui.rightClick(fish_location.left, fish_location.top)
            continue  # Revenir au début de la boucle pour re-tenter la détection
        print("battle.png trouvé, passage à l'étape suivante.")

        # Étape 4: Chercher opt1.png, sinon opt2.png
        print("Recherche de opt1.png...")
        time.sleep(1)  # Petite pause avant de chercher opt1.png
        if not find_image_with_timeout_and_click("fish/opt1.png", 5, 'left'):
            print("opt1.png non trouvé après 5 secondes, recherche de opt2.png...")
            if not find_image_with_timeout_and_click("fish/opt2.png", 5, 'left'):
                print("opt2.png non trouvé, exécution de la commande de secours...")
                emergency_commands()
                print("Commande de secours exécutée, reprise de la surveillance...")
                continue
            else:
                print("Clique effectué sur opt2.png, passage à l'étape suivante.")
        else:
            print("Clique effectué sur opt1.png, passage à l'étape suivante.")

        # Étape 5: Cliquer plusieurs fois sur clic droit jusqu'à trouver finish.png
        print("Recherche de finish.png en cliquant à droite...")
        start_time = time.time()
        found = False
        while not found:
            if time.time() - start_time > 8:  # Si plus de 8 secondes se sont écoulées
                emergency_commands()  # Exécuter les commandes de secours
                break  # Sortir de la boucle
            # Continuer à chercher et cliquer
            found = find_and_click("fish/finish.png", 'right')
            if not found:
                pyautogui.rightClick()
        print("finish.png trouvé et cliqué.")

        # Étape 6: Cliquer sur finish.png et faire un clic droit pour recommencer
        find_and_click("fish/finish.png")
        print("Pause avant de recommencer...")
        time.sleep(1)  # Petite pause avant de recommencer
        print("Reprise de la surveillance...")


main_routine_with_logs()  # Décommentez cette ligne pour exécuter le script.
