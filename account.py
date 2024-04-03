import json
import os
import string
import secrets


def generer_mot_de_passe():
    # Inclure lettres, chiffres, et uniquement "!" et "?"
    caracteres_speciaux = "!?"
    alphabet = string.ascii_letters + string.digits + caracteres_speciaux
    while True:
        mot_de_passe = ''.join(secrets.choice(alphabet) for _ in range(10))
        if (any(c.islower() for c in mot_de_passe)
                and any(c.isupper() for c in mot_de_passe)
                and sum(c.isdigit() for c in mot_de_passe) >= 3
                and any(c in caracteres_speciaux for c in mot_de_passe)):
            break
    return mot_de_passe


def verifier_et_creer_donnees():
    pseudos_supplementaires = [
        "WhisperingWisp", "FrostedFern", "CrimsonCraze", "VelvetVortex",
        "EchoingEmber", "SapphireSpecter", "TwilightTinker", "PhantomPioneer",
        "ObsidianOrbit", "ArcaneAlchemist", "BreezyBlade", "DuskDreamer",
        "PolarProwler", "FluxFable", "MirageMariner", "NeonNebula",
        "WanderingWillow", "SilkenShadow", "GlacialGambit", "CelestialCipher"
    ]

    donnees_existantes = charger_donnees()
    pseudos_existants = [compte["username"]
                         for compte in donnees_existantes.get("comptes", [])]
    nouveaux_pseudos = [
        pseudo for pseudo in pseudos_supplementaires if pseudo not in pseudos_existants]

    if nouveaux_pseudos:
        id_suivant = len(pseudos_existants) + 1
        comptes_supplementaires = [
            {"id": i+id_suivant,
             "username": pseudo,
             "motDePasse": generer_mot_de_passe(),
             "proxy": "adresse.proxy.com",
             "port": 8080,
             "usernameProxy": "UsernameProxy",
             "mdpProxy": "MdpProxy",
             "status": "non défini"}
            for i, pseudo in enumerate(nouveaux_pseudos)
        ]

        donnees_existantes["comptes"].extend(comptes_supplementaires)
        sauvegarder_donnees(donnees_existantes)

    return charger_donnees()


def sauvegarder_donnees(donnees):
    with open('donnees.json', 'w') as fichier:
        json.dump(donnees, fichier, indent=4)


def charger_donnees():
    try:
        with open('donnees.json', 'r') as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


donnees = verifier_et_creer_donnees()

for compte in donnees.get("comptes", []):
    print(compte)
