"""
Vérifie les photos des produits : chaque produit, sa photo (lue dans photos_produits.py),
et si le fichier existe dans "static".
Lancer dans le dossier backend :   python verifier_photos.py
Ce programme ne modifie rien.
"""
import os
from datetime import datetime

from sqlalchemy import text

from app import app, db
from photos_produits import PHOTOS, PHOTO_PAR_DEFAUT

DOSSIER_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def infos_fichier(nom):
    chemin = os.path.join(DOSSIER_STATIC, nom)
    if not os.path.exists(chemin):
        return None
    return os.path.getsize(chemin) // 1024, datetime.fromtimestamp(os.path.getmtime(chemin)).strftime("%d/%m/%Y %H:%M")


with app.app_context():
    try:
        lignes = db.session.execute(text(
            "SELECT id, espace, ordre, nom FROM produits WHERE espace IS NOT NULL ORDER BY espace, ordre, id")).fetchall()
    except Exception as erreur:
        print("Impossible de lire les produits :", erreur)
        raise SystemExit(1)

    problemes = 0
    utilisees = {}
    noms_connus = set()
    for id_, espace, ordre, nom in lignes:
        noms_connus.add((espace, nom))
        utilisees.setdefault(PHOTOS.get((espace, nom), PHOTO_PAR_DEFAUT), []).append(f"{nom} ({espace})")

    espace_actuel = None
    for id_, espace, ordre, nom in lignes:
        if espace != espace_actuel:
            espace_actuel = espace
            print(f"\n=== {espace} ===")
        photo = PHOTOS.get((espace, nom))
        par_defaut = photo is None
        photo = photo or PHOTO_PAR_DEFAUT
        infos = infos_fichier(photo)
        if infos is None:
            etat = "FICHIER ABSENT du dossier static"
            problemes += 1
        else:
            taille, date = infos
            etat = f"OK, {taille} Ko, copié le {date}"
            if taille > 500:
                etat += " (lourde : réduis-la)"
        if par_defaut:
            etat += " | PAS DE LIGNE dans photos_produits.py : photo par défaut"
            problemes += 1
        partage = [p for p in utilisees[photo] if not p.startswith(nom + " (")]
        suite = f" | même photo que : {', '.join(partage)}" if partage else ""
        print(f"  {ordre or '-'}. {nom}  ->  {photo}  [{etat}]{suite}")

    inutiles = [cle for cle in PHOTOS if cle not in noms_connus]
    if inutiles:
        print("\nLIGNES DE photos_produits.py QUI NE CORRESPONDENT À AUCUN PRODUIT (faute de frappe dans l'espace ou le nom ?) :")
        for espace, nom in inutiles:
            print(f"  - ({espace!r}, {nom!r})")
        problemes += len(inutiles)

    print("\n" + "-" * 60)
    print(f"{problemes} problème(s) à regarder." if problemes else "Tout est en ordre : chaque produit a sa ligne et son fichier existe.")
    print("Une photo partagée entre plusieurs produits est normale tant que tu n'as pas mis la photo définitive.")