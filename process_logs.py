import json
import re
import sys

chemin_log = r"C:\MultiMc\instances\1.12.2\.minecraft\logs\latest.log"
chemin_json = r"C:\wamp64\www\data_view\data.json"

# Fonction pour charger les données du fichier JSON


def charger_donnees(chemin):
    try:
        with open(chemin, 'r', encoding='ISO-8859-1') as fichier:
            return json.load(fichier)
    except (FileNotFoundError, json.JSONDecodeError):
        # Retourne une structure par défaut si le fichier n'existe pas ou est vide
        return {"pokemon": []}

# Fonction pour sauvegarder les données dans le fichier JSON


def sauvegarder_donnees(donnees, chemin):
    with open(chemin, 'w', encoding='ISO-8859-1') as fichier:
        json.dump(donnees, fichier, indent=4)

# Fonction pour extraire les IVs de Pokémon depuis le fichier de logs


def extraire_ivs_pokemon(chemin_log):
    regex_ivs = r"\[CHAT\] (.+ IVs): §e(\d+)"
    ivs = {}
    try:
        with open(chemin_log, 'r', encoding='ISO-8859-1') as fichier:
            for ligne in fichier:
                correspondance = re.findall(regex_ivs, ligne)
                for stat, valeur in correspondance:
                    cle_stat = stat.lower().replace(" ivs", "").replace(".", "").replace(" ", "_")
                    cle_stat = cle_stat.replace("attack", "atk").replace(
                        "defence", "def").replace("sp_attack", "spa").replace("sp_defence", "spd")
                    ivs[cle_stat] = int(valeur)
    except FileNotFoundError:
        print(f"Le fichier {chemin_log} n'a pas été trouvé.")
    return ivs

# Fonction pour ajouter les IVs au fichier JSON


def ajouter_ivs_au_json(chemin_json, ivs, pseudo_dresseur):
    donnees = charger_donnees(chemin_json)
    # Structure modifiée pour inclure le pseudo du joueur dans l'entrée Pokémon
    pokemon = {
        "trainer": pseudo_dresseur,
        "ivs": ivs
    }
    donnees["pokemon"].append(pokemon)
    sauvegarder_donnees(donnees, chemin_json)


# Exécution
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_logs.py <pseudo_dresseur>")
    else:
        # Récupération du pseudo du joueur passé comme argument
        pseudo_dresseur = sys.argv[1]
        ivs = extraire_ivs_pokemon(chemin_log)
        if ivs:
            ajouter_ivs_au_json(chemin_json, ivs, pseudo_dresseur)
            print("Les IVs ont été ajoutés au fichier JSON.")
        else:
            print("Aucun IVs trouvé dans le fichier de logs.")
