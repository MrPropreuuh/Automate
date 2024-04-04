from PIL import Image
import os

def redimensionner_et_sauvegarder_image(source_path, target_folder, target_width):
    # Vérifier si le dossier cible existe, sinon le créer
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    for img_name in os.listdir(source_path):
        if img_name.endswith((".png", ".jpg", ".jpeg")):  # Vérifier le format de l'image
            full_path = os.path.join(source_path, img_name)
            image = Image.open(full_path)
            ratio = target_width / image.width
            target_height = round(image.height * ratio)
            resized_image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)  # Mise à jour ici
            
            # Construire le chemin complet pour la sauvegarde de l'image redimensionnée
            save_path = os.path.join(target_folder, img_name)
            resized_image.save(save_path)
            print(f"Image {img_name} redimensionnée et sauvegardée en {save_path}.")

# Chemin vers le dossier contenant les images originales
source_folder = 'images'

# Chemin vers le dossier où sauvegarder les images redimensionnées
target_folder = 'images1080'

# Largeur cible pour le redimensionnement (pour 1080p, ajustez selon vos besoins)
target_width = 1920

# Appel de la fonction
redimensionner_et_sauvegarder_image(source_folder, target_folder, target_width)
