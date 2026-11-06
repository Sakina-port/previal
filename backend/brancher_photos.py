"""
Branche les photos des produits sur le fichier photos_produits.py.
A lancer UNE SEULE FOIS, dans le dossier backend :   python brancher_photos.py
Chaque fichier modifié est copié en "nom.avant-photos". Si une ligne attendue manque, RIEN n'est modifié.
"""
import re
import shutil
import sys


class Fichier:
    def __init__(self, chemin):
        self.chemin = chemin
        with open(chemin, encoding="utf-8") as f:
            self.texte = f.read()
        self.problemes = []

    def regex(self, etiquette, motif, nouveau, attendu=1):
        trouve = len(re.findall(motif, self.texte))
        if trouve == attendu:
            fonction = nouveau if callable(nouveau) else (lambda m: nouveau)
            self.texte = re.sub(motif, fonction, self.texte)
            print(f"[OK ] {self.chemin} : {etiquette}")
        else:
            print(f"[PROBLEME] {self.chemin} : {etiquette} : trouvé {trouve} fois, attendu {attendu}")
            self.problemes.append(f"{self.chemin} : {etiquette}")


def main():
    try:
        app_py = Fichier("app.py")
        liste = Fichier("templates/liste_produits.html")
        fiche = Fichier("templates/produit.html")
    except FileNotFoundError as erreur:
        print(f"Fichier introuvable : {erreur.filename}. Lance ce programme depuis le dossier backend.")
        sys.exit(1)

    if "photo_du_produit" in app_py.texte:
        print("Les photos sont déjà branchées sur photos_produits.py : rien à faire.")
        return
    try:
        open("photos_produits.py", encoding="utf-8").close()
    except FileNotFoundError:
        print("Crée d'abord le fichier photos_produits.py (dans le dossier backend), puis relance.")
        sys.exit(1)

    app_py.regex("importer photos_produits", r"(from stockage import [^\n]*\n)",
                 lambda m: m.group(1) + "from photos_produits import photo_du_produit\n")
    app_py.regex("donner photo_produit aux pages", r"configurer_mail\(app\)\n",
                 'configurer_mail(app)\napp.jinja_env.globals["photo_produit"] = photo_du_produit\n')
    liste.regex("photo lue dans photos_produits.py", r"\(produit\.photo or '[^']*'\)", "photo_produit(produit)")
    fiche.regex("photo lue dans photos_produits.py", r"\(produit\.photo or '[^']*'\)", "photo_produit(produit)")

    problemes = [p for f in (app_py, liste, fiche) for p in f.problemes]
    if problemes:
        print("\nRIEN n'a été modifié. Envoie-moi ces lignes. Si tu lis « trouvé 0 fois » pour les pages de produits,")
        print("lance d'abord python appliquer_produits.py.")
        sys.exit(1)

    for f in (app_py, liste, fiche):
        shutil.copyfile(f.chemin, f.chemin + ".avant-photos")
        with open(f.chemin, "w", encoding="utf-8", newline="") as sortie:
            sortie.write(f.texte)
    print("\nTERMINÉ. Les photos se changent maintenant dans photos_produits.py.")
    print("Relance le site (Ctrl+C puis python app.py).")


main()