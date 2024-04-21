import json
import re
import sys

chemin_log = r"C:\Users\vince\Desktop\Tout\MultiMC\instances\1.16.5\.minecraft\logs\latest.log"
chemin_json = r"D:\wamp64\www\data_view\data.json"


def charger_donnees(chemin):
    try:
        with open(chemin, 'r', encoding='ISO-8859-1') as fichier:
            return json.load(fichier)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pokemon": []}


def sauvegarder_donnees(donnees, chemin):
    with open(chemin, 'w', encoding='ISO-8859-1') as fichier:
        json.dump(donnees, fichier, indent=4)


def extraire_ivs_pokemon(chemin_log):
    regex_ivs = r"\[CHAT\] (.+): (\d+)"
    ivs = {}
    try:
        with open(chemin_log, 'r', encoding='ISO-8859-1') as fichier:
            for ligne in fichier:
                match = re.search(regex_ivs, ligne)
                if match:
                    stat, valeur = match.groups()
                    cle_stat = stat.lower().replace("ivs", "").replace(" ", "_").strip(":")
                    ivs[cle_stat] = int(valeur)
    except FileNotFoundError:
        print(f"Le fichier {chemin_log} n'a pas été trouvé.")
    return ivs


def ajouter_ivs_au_json(chemin_json, ivs, pseudo_dresseur):
    donnees = charger_donnees(chemin_json)
    ivs["trainer"] = pseudo_dresseur
    donnees["pokemon"].append(ivs)
    sauvegarder_donnees(donnees, chemin_json)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_logs.py <pseudo_dresseur>")
    else:
        pseudo_dresseur = sys.argv[1]
        ivs = extraire_ivs_pokemon(chemin_log)
        if ivs:
            ajouter_ivs_au_json(chemin_json, ivs, pseudo_dresseur)
            print("Les IVs ont été ajoutés au fichier JSON.")
        else:
            print("Aucun IVs trouvé dans le fichier de logs.")
