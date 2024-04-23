from screeninfo import get_monitors
import pyautogui


def capture_and_save_screenshot(region):
    # Capture une région spécifiée de l'écran
    screenshot = pyautogui.screenshot(region=region)
    # Sauvegardez la capture d'écran dans un fichier
    screenshot.save("screenshot_display2.png")


region = (0, 0, 1920, 1080)
capture_and_save_screenshot(region)
