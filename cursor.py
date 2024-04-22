from pynput.mouse import Controller as MouseController, Button
import time

mouse = MouseController()


def afficher_position_curseur():
    """
    Affiche la position du curseur toutes les 1 seconde.
    Prévu pour un écran de 2560x1440 pixels.
    """
    try:
        while True:
            position = mouse.position  # Obtient la position actuelle du curseur
            print("Position du curseur :", position)
            time.sleep(1)  # Pause de 1 seconde avant la prochaine itération
    except KeyboardInterrupt:
        # Message affiché lors de l'interruption manuelle par l'utilisateur (Ctrl+C)
        print("Arrêté par l'utilisateur.")


# Exemple d'utilisation des fonctions
# Cette fonction tournera en boucle jusqu'à interruption par l'utilisateur
afficher_position_curseur()
