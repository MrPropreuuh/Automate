from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button
import pyautogui
from pynput.keyboard import Controller, Key
keyboard = Controller()
mouse = MouseController()

pyautogui.sleep(3)
print(
    "Page d'enregistrement détectée.")
keyboard.press(Key.enter)
pyautogui.sleep(1)
pyautogui.write(
    f'/register tg tg')
keyboard.press(Key.enter)
pyautogui.sleep(1)

keyboard.press('1')
keyboard.release('1')
pyautogui.sleep(1)
mouse.click(Button.right, 1)
