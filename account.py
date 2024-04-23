import json
import os
import random
import string
import secrets


def generer_mot_de_passe():
    caracteres_speciaux = "!?"
    alphabet = string.ascii_letters + string.digits + caracteres_speciaux
    while True:
        mot_de_passe = ''.join(secrets.choice(alphabet) for _ in range(10))
        if (any(c.islower() for c in mot_de_passe) and
            any(c.isupper() for c in mot_de_passe) and
            sum(c.isdigit() for c in mot_de_passe) >= 3 and
                any(c in caracteres_speciaux for c in mot_de_passe)):
            break
    return mot_de_passe


def verifier_et_creer_donnees():
    mots = ["Crys", "Nebul", "Vorte", "Shado", "Quant", "Glitz", "Echor", "Flame", "Nexus", "Glyph",
            "Mysto", "Rifte", "Zenit", "Abyss", "Pulse", "Spect", "Tides", "Orbit", "Drift", "Archa",
            "Dusky", "Frost", "Blaze", "Phant", "Sages", "Whisp", "Zephy", "Ember", "Cindr", "Toren",
            "Vivid", "Voidy", "Mythi", "Bligh", "Bloom", "Forge", "Gales", "Haven", "Lumen", "Maels",
            "Peaks", "Radia", "Surge", "Tempe", "Vextr", "Wilde", "Zenon", "Alpha", "Omega"]
    suffixes = ["War", "Magi", "Rogu", "Knit", "Hunt", "Prie", "Sorc", "Pala"]

    donnees_existantes = charger_donnees()
    pseudos_existants = [compte["username"]
                         for compte in donnees_existantes["comptes"]]

    pseudos_supplementaires = []
    while len(pseudos_supplementaires) < 50:
        mot = random.choice(mots)
        suffixe = random.choice(suffixes)
        numero = random.randint(10, 999)
        pseudo = f"{mot}{suffixe}{numero}"
        if pseudo not in pseudos_existants and len(pseudo) <= 16:
            pseudos_supplementaires.append(pseudo)

    nouveaux_pseudos = [
        pseudo for pseudo in pseudos_supplementaires if pseudo not in pseudos_existants]

    if nouveaux_pseudos:
        id_suivant = len(pseudos_existants) + 1
        comptes_supplementaires = [{
            "id": i + id_suivant,
            "username": pseudo,
            "motDePasse": generer_mot_de_passe(),
            "proxy": "adresse.proxy.com",
            "port": 8080,
            "usernameProxy": "UsernameProxy",
            "mdpProxy": "MdpProxy",
            "status": "non défini",
            "today": "false",
            "ivsCheck": "false",
            "daily": 1,
            "dailyComplete": "false"
        } for i, pseudo in enumerate(nouveaux_pseudos)]

        donnees_existantes["comptes"].extend(comptes_supplementaires)
        sauvegarder_donnees(donnees_existantes)

    return charger_donnees()


def sauvegarder_donnees(donnees):
    with open('donnees2.json', 'w') as fichier:
        json.dump(donnees, fichier, indent=4)


def charger_donnees():
    try:
        with open('donnees2.json', 'r') as fichier:
            donnees = json.load(fichier)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialisation d'un dictionnaire vierge avec une liste de comptes vide
        donnees = {"comptes": []}
    return donnees


donnees = verifier_et_creer_donnees()
for compte in donnees["comptes"]:
    print(compte)
