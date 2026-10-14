import os


DOSSIER_STOCKAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"stockage")

def enregistrer_fichier(contenu, nom_stocke):
    os.makedirs(DOSSIER_STOCKAGE, exist_ok=True)
    chemin = os.path.join(DOSSIER_STOCKAGE, nom_stocke)
    with open (chemin, "wb") as fichier:
        fichier.write(contenu)
def lire_fichier(nom_stocke):
    chemin = os.path.join(DOSSIER_STOCKAGE, os.path.basename(nom_stocke))
    with open(chemin, "rb") as fichier:
        return fichier.read()