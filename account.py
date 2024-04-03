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
    pseudos = [
        "MysticWander", "EchoFrostbite", "TwilightHarbor", "QuantumSquid",
        "EmberScribe", "SilentCrafter", "PixelPilgrim", "SunlitGlitch",
        "NeonNomad", "CrypticNebula", "AzurePhantom", "RandomVoyager",
        "ForgottenMirth", "ElementalDrift", "ShadowSculptor", "FabledStrider",
        "VoidGlimmer", "CelestialRiddle", "LunarLurker", "SolarSpectre",
        "PhantomQuill", "ChaosWeaver", "SereneStardust", "AbyssalEcho",
        "CosmicDrifter", "NetherNomad", "EtherealEngineer", "MirageMason",
        "StarlitSmith", "DreamDiver"
    ]

    if not os.path.exists('donnees.json') or os.stat('donnees.json').st_size == 0:
        donnees = {
            "comptes": [
                {"id": i+1,
                 "username": pseudo,
                 "motDePasse": generer_mot_de_passe(),
                 "proxy": "adresse.proxy.com",
                 "port": 8080,
                 "usernameProxy": "UsernameProxy",
                 "mdpProxy": "MdpProxy",
                 "status": "non défini"}
                for i, pseudo in enumerate(pseudos)
            ]
        }
        sauvegarder_donnees(donnees)
    return charger_donnees()


def sauvegarder_donnees(donnees):
    with open('donnees.json', 'w') as fichier:
        json.dump(donnees, fichier, indent=4)


def charger_donnees():
    try:
        with open('donnees.json', 'r') as fichier:
            return json.load(fichier)
    except json.JSONDecodeError:
        return {}


donnees = verifier_et_creer_donnees()

for compte in donnees.get("comptes", []):
    print(compte)
