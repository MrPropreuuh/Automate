import json
import os

# Charger les données des comptes


def charger_donnees(nom_fichier='donnees.json'):
    if os.path.exists(nom_fichier):
        with open(nom_fichier, 'r') as fichier:
            return json.load(fichier)
    else:
        return {"comptes": []}

# Sauvegarder les données mises à jour


def sauvegarder_donnees(donnees, nom_fichier='donnees.json'):
    with open(nom_fichier, 'w') as fichier:
        json.dump(donnees, fichier, indent=4)

# Charger la blacklist des proxies


def charger_blacklist(nom_fichier='blacklist.json'):
    if os.path.exists(nom_fichier):
        with open(nom_fichier, 'r') as fichier:
            return json.load(fichier)
    else:
        return []

# Sauvegarder la blacklist mise à jour


def sauvegarder_blacklist(blacklist, nom_fichier='blacklist.json'):
    with open(nom_fichier, 'w') as fichier:
        json.dump(blacklist, fichier, indent=4)

# Charger les proxies depuis un fichier texte


def charger_proxies(nom_fichier='proxy.txt'):
    with open(nom_fichier, 'r') as fichier:
        return [ligne.strip() for ligne in fichier.readlines()]

# Script principal


def mettre_a_jour_proxies():
    donnees = charger_donnees()
    blacklist = charger_blacklist()
    proxies = charger_proxies()

    compteur_mis_a_jour = 0
    compteur_ignores = 0

    for compte in donnees['comptes']:
        for proxy in proxies:
            if proxy not in blacklist:
                ip, port = proxy.split(':')
                compte['proxy'] = ip
                compte['port'] = int(port)
                blacklist.append(proxy)
                compteur_mis_a_jour += 1
                print(
                    f"Proxy {proxy} attribué au compte {compte['username']}.")
                break
        else:
            print(f"Aucun proxy disponible pour {compte['username']}, ignoré.")
            compteur_ignores += 1

    sauvegarder_donnees(donnees)
    sauvegarder_blacklist(blacklist)

    print(f"{compteur_mis_a_jour} comptes mis à jour. {compteur_ignores} comptes ignorés.")


if __name__ == '__main__':
    mettre_a_jour_proxies()
