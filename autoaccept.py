from pynput import keyboard
from pynput.keyboard import Key, Controller
import time

keyboard_controller = Controller()


def on_press(key):
    try:
        # Vérifie si la touche 'P' a été pressée
        if key.char == 'p':
            # Début de la macro 1
            keyboard_controller.press(Key.enter)
            keyboard_controller.release(Key.enter)
            time.sleep(1)
            keyboard_controller.type('/tpaaccept')
            keyboard_controller.press(Key.enter)
            keyboard_controller.release(Key.enter)
            # Fin de la macro 1

        # Vérifie si la touche 'O' a été pressée
        elif key.char == 'o':
            # Début de la macro 2
            keyboard_controller.press(Key.enter)
            keyboard_controller.release(Key.enter)
            time.sleep(1)
            keyboard_controller.type('/tpaaccept')
            keyboard_controller.press(Key.enter)
            keyboard_controller.release(Key.enter)
            time.sleep(5)
            keyboard_controller.press('s')  # Appuyez sur 'S'
            time.sleep(2)
            keyboard_controller.release('s')  # Relâchez 'S'
            time.sleep(10)
            keyboard_controller.press('w')  # Appuyez sur 'W'
            time.sleep(2)
            keyboard_controller.release('w')  # Relâchez 'W'
            # Fin de la macro 2
    except AttributeError:
        pass  # Gère le cas où une touche spéciale est pressée


def on_release(key):
    print("test")


# Collecte les événements de pression de touche jusqu'à ce qu'on presse 'Echap'
with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()
