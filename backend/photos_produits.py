"""
LES PHOTOS DES PRODUITS : c'est ici, et seulement ici, que tu changes ou ajoutes un nom de photo.

Chaque ligne relie un produit à un fichier du dossier "static".
  - La clé est ("espace", "nom du produit"), écrite EXACTEMENT comme sur le site.
  - Le nom du fichier doit être identique à celui du dossier static (mêmes lettres, avec .jpg).
Pour un nouveau produit : ajoute une ligne. S'il n'y a pas de ligne, la photo par défaut est utilisée.
Après une modification : enregistre (Ctrl+S) et recharge le site (Ctrl+F5).
Pour vérifier :  python verifier_photos.py
"""

PHOTO_PAR_DEFAUT = "particulier.jpg"

PHOTOS = {
    # ----- Particuliers -----
    ("Particuliers", "Mutuelle santé particuliers"): "mu-san.jpg",
    ("Particuliers", "Mutuelle santé seniors"): "senior.jpg",
    ("Particuliers", "Prévoyance"): "prevoyance-part.jpg",
    ("Particuliers", "Assurance emprunteur"): "ass-emp.jpg",
    ("Particuliers", "Plan Épargne Retraite (PER)"): "per.jpg",
    ("Particuliers", "Habitation"): "habitation.jpg",
    ("Particuliers", "Automobile"): "auto.jpg",

    # ----- Professionnels -----
    ("Professionnels", "Mutuelle (collectif)"): "mu-pro.jpg",
    ("Professionnels", "Prévoyance (collectif)"): "prevo-pro.jpg",
    ("Professionnels", "Assurance emprunteur"): "ass-emp.jpg",
    ("Professionnels", "Multirisque professionnel"): "multi-pro.jpg",
    ("Professionnels", "Responsabilité civile professionnelle"): "rcp.jpg",
    ("Professionnels", "Assurance automobile"): "auto-pro.jpg",
    ("Professionnels", "Assurance PNO professionnelle"): "ass-pno.jpg",

    # ----- Dirigeants -----
    ("Dirigeants", "Mutuelle TNS"): "sante1.jpg",
    ("Dirigeants", "Prévoyance TNS"): "prevoyance.jpg",
    ("Dirigeants", "Complémentaire retraite / PER"): "per.jpg",
    ("Dirigeants", "Assurance Homme clé"): "diri-senior.jpg",
}


def photo_du_produit(produit):
    return PHOTOS.get((produit.espace, produit.nom), PHOTO_PAR_DEFAUT)