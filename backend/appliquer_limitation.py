"""
LIMITATION DES TENTATIVES DE CONNEXION

A lancer UNE SEULE FOIS, dans le dossier backend, après :   pip install Flask-Limiter
    python appliquer_limitation.py

Règle appliquée à chaque route de connexion (/equipe, et /compte si l'espace client est activé) :
  - 5 tentatives par minute et 20 par heure, par adresse IP ;
  - seules les tentatives ÉCHOUÉES comptent (une connexion réussie ne compte pas) ;
  - au-delà, la page répond 429 « Trop de tentatives », même si le mot de passe saisi est le bon ;
  - le message d'erreur reste générique : il ne dit jamais si l'e-mail existe.

Ce programme modifie app.py (imports, réglage, 2 décorateurs) et requirements.txt.
Chaque fichier est copié en "nom.avant-limitation". Si une ligne attendue manque, RIEN n'est modifié.
"""
import os
import re
import shutil
import sys

try:
    import flask_limiter  # noqa: F401
except ImportError:
    print("Flask-Limiter n'est pas installé. Tape d'abord :   pip install Flask-Limiter   puis relance ce programme.")
    sys.exit(1)

BLOC_LIMITEUR = '''
# Limitation des tentatives de connexion : 5 par minute et 20 par heure, par adresse IP, échecs seulement.
# Les compteurs sont gardés en mémoire (un seul serveur). Pour plusieurs serveurs : LIMITEUR_STOCKAGE=redis://... dans .env
limiter = Limiter(get_remote_address, app=app, default_limits=[], strategy="moving-window", headers_enabled=True,
                  storage_uri=os.getenv("LIMITEUR_STOCKAGE", "memory://"))
LIMITES_CONNEXION = "5 per minute;20 per hour"


@app.errorhandler(429)
def trop_de_tentatives(erreur):
    message = "Trop de tentatives de connexion. Réessayez dans quelques minutes."
    app.logger.warning("Limite de tentatives atteinte : %s sur %s", request.remote_addr, request.path)
    try:
        if request.path.startswith("/equipe"):
            return render_template("equipe_connexion.html", erreur=message), 429
        if request.path.startswith("/compte"):
            return render_template("compte.html", erreur=message), 429
    except Exception:   # même si la page ne peut pas s'afficher, la réponse reste un refus clair
        pass
    return Response(message, status=429, mimetype="text/plain; charset=utf-8")
'''

DECORATEUR = '@limiter.limit(LIMITES_CONNEXION, methods=["POST"], deduct_when=lambda reponse: reponse.status_code == 200)\n'


class Fichier:
    def __init__(self, chemin):
        self.chemin = chemin
        with open(chemin, encoding="utf-8") as f:
            self.texte = f.read()
        self.original = self.texte
        self.problemes = []

    def une_fois(self, etiquette, ancien, nouveau, obligatoire=True):
        n = self.texte.count(ancien)
        if n == 1:
            self.texte = self.texte.replace(ancien, nouveau)
            print(f"[OK ] {self.chemin} : {etiquette}")
        elif obligatoire:
            print(f"[PROBLEME] {self.chemin} : {etiquette} : trouvé {n} fois, attendu 1")
            self.problemes.append(f"{self.chemin} : {etiquette}")
        else:
            print(f"[-- ] {self.chemin} : {etiquette} : non trouvé, laissé tel quel")


def main():
    if not os.path.exists("app.py"):
        print("app.py est introuvable : lance ce programme depuis le dossier backend.")
        sys.exit(1)

    app_py = Fichier("app.py")
    fichiers = [app_py]

    if "Limiter(" in app_py.texte:
        print("[OK ] app.py : la limitation est déjà installée")
    else:
        app_py.une_fois("import de Flask-Limiter", "from dotenv import load_dotenv\n",
                        "from dotenv import load_dotenv\nfrom flask_limiter import Limiter\nfrom flask_limiter.util import get_remote_address\n")
        app_py.une_fois("réglage de la limitation et message « trop de tentatives »", 'login_manager.login_view = "compte"\n',
                        'login_manager.login_view = "compte"\n' + BLOC_LIMITEUR)
        app_py.une_fois("limite sur la connexion de l'équipe (/equipe)",
                        '@app.route("/equipe", methods=["GET", "POST"])\ndef equipe_connexion():\n',
                        '@app.route("/equipe", methods=["GET", "POST"])\n' + DECORATEUR + "def equipe_connexion():\n")
        app_py.une_fois("limite sur la connexion client (/compte, fonction masquée)",
                        '@app.route("/compte", methods=["GET", "POST"])\ndef compte():\n',
                        '@app.route("/compte", methods=["GET", "POST"])\n' + DECORATEUR + "def compte():\n",
                        obligatoire=False)

    if os.path.exists("requirements.txt"):
        with open("requirements.txt", encoding="utf-8") as f:
            contenu = f.read()
        if re.search(r"^flask-limiter\b", contenu, re.I | re.M):
            print("[OK ] requirements.txt : Flask-Limiter est déjà listé")
        else:
            r = Fichier("requirements.txt")
            r.texte = r.texte.rstrip("\n") + "\nFlask-Limiter\n"
            fichiers.append(r)
            print("[OK ] requirements.txt : Flask-Limiter ajouté")
    else:
        print("[-- ] requirements.txt introuvable : ajoute la ligne Flask-Limiter dans ton fichier de dépendances")

    problemes = [p for f in fichiers for p in f.problemes]
    if problemes:
        print("\nRIEN n'a été modifié. Envoie-moi ces lignes et colle-moi le fichier concerné :")
        for p in problemes:
            print("  -", p)
        sys.exit(1)

    ecrits = []
    for f in fichiers:
        if f.texte != f.original:
            shutil.copyfile(f.chemin, f.chemin + ".avant-limitation")
            with open(f.chemin, "w", encoding="utf-8", newline="") as sortie:
                sortie.write(f.texte)
            ecrits.append(f.chemin)
    print("\nTERMINÉ." if ecrits else "\nRien à modifier : tout est déjà en place.")
    for chemin in ecrits:
        print("  -", chemin)
    print("\nÉtape suivante : relance le site (Ctrl+C, puis python app.py), puis lance :   python verifier_limitation.py")


main()