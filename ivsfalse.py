import json


def reset_ivsCheck_to_false():
    # Chemin vers le fichier JSON contenant les données
    fichier_donnees = 'donnees.json'

    # Tenter d'ouvrir et lire le fichier de données
    try:
        with open(fichier_donnees, 'r') as fichier:
            donnees = json.load(fichier)
    except FileNotFoundError:
        print("Le fichier n'a pas été trouvé.")
        return
    except json.JSONDecodeError:
        print("Erreur de décodage JSON.")
        return

    # Vérification que la clé 'comptes' existe dans le dictionnaire chargé
    if 'comptes' not in donnees:
        print("La clé 'comptes' n'existe pas dans le fichier JSON.")
        return

    # Mise à jour du champ 'ivsCheck' pour chaque compte
    comptes_modifies = False
    for compte in donnees['comptes']:
        if compte['ivsCheck'] != "false":
            compte['ivsCheck'] = "false"
            comptes_modifies = True

    # Si des modifications ont été apportées, sauvegarder les changements dans le fichier
    if comptes_modifies:
        try:
            with open(fichier_donnees, 'w') as fichier:
                json.dump(donnees, fichier, indent=4, ensure_ascii=False)
            print("Tous les champs 'ivsCheck' ont été mis à 'false'.")
        except IOError:
            print("Erreur lors de l'écriture dans le fichier.")
    else:
        print("Aucun champ 'ivsCheck' n'a été modifié.")


# Exécuter la fonction pour mettre à jour le fichier JSON
reset_ivsCheck_to_false()
