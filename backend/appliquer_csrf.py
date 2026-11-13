"""
PROTECTION CSRF GLOBALE DE PREVIAL

A lancer UNE SEULE FOIS, dans le dossier backend, après :   pip install Flask-WTF
    python appliquer_csrf.py

Ce programme :
  1. app.py : active la protection sur TOUTES les routes (POST, PUT, PATCH et DELETE) et affiche une page claire si le
     jeton est absent ou périmé ; la route /refuser, qui modifiait des données par un simple lien, devient POST ;
  2. templates/*.html : ajoute le jeton caché dans chaque formulaire POST ;
  3. assistant.py : l'assistant envoie le jeton dans l'en-tête de ses requêtes ;
  4. requirements.txt : ajoute Flask-WTF ;
  5. crée templates/session_expiree.html (la page affichée quand le jeton est refusé).
Chaque fichier modifié est copié en "nom.avant-csrf". Si une ligne attendue manque, RIEN n'est modifié.
"""
import glob
import os
import re
import shutil
import sys

try:
    import flask_wtf  # noqa: F401
except ImportError:
    print("Flask-WTF n'est pas installé. Tape d'abord :   pip install Flask-WTF   puis relance ce programme.")
    sys.exit(1)

JETON = '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'
FORMULAIRE_POST = re.compile(r'<form\b[^>]*?\bmethod\s*=\s*["\']?post["\']?[^>]*>', re.I)
FORMULAIRE_TOUS = re.compile(r'<form\b[^>]*>', re.I)

BLOC_INIT = '''csrf = CSRFProtect(app)   # contrôle le jeton CSRF sur POST, PUT, PATCH et DELETE, pour toutes les routes


@app.errorhandler(CSRFError)
def jeton_csrf_invalide(erreur):
    message = "Votre session a expiré ou la page est trop ancienne. Rechargez la page, puis recommencez."
    if request.is_json:
        return Response(json.dumps({"ok": False, "reponse": message}, ensure_ascii=False), status=400, mimetype="application/json")
    try:
        return render_template("session_expiree.html", message=message), 400
    except Exception:   # même si la page ne peut pas s'afficher, la requête reste refusée proprement
        return Response("<p>" + message + "</p>", status=400, mimetype="text/html")
'''

PAGE_SESSION_EXPIREE = """{% extends "base.html" %}

{% block title %}PREVIAL : page expirée{% endblock %}

{% block content %}
<link rel="stylesheet" href="{{ url_for('static', filename='previal-pages.css') }}">
<section class="pv-bandeau">
  <div class="acc-conteneur">
    <h1>Page expirée</h1>
  </div>
</section>
<section style="padding: 48px 0 80px;">
  <div class="acc-conteneur" style="max-width: 720px;">
    <p style="font-size: 1.1rem; line-height: 1.7;">{{ message }}</p>
    <p style="display: flex; flex-wrap: wrap; gap: 12px;">
      <a class="acc-btn acc-btn-bleu" href="javascript:history.back()">Revenir à la page précédente</a>
      <a class="acc-btn acc-btn-ligne" href="/">Retour à l'accueil</a>
    </p>
  </div>
</section>
{% endblock %}
"""


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
            print(f"[-- ] {self.chemin} : {etiquette} : non trouvé (déjà modifié ?), laissé tel quel")

    def modifie(self):
        return self.texte != self.original


def proteger_formulaires(fichier):
    """Ajoute le jeton après chaque balise <form method="post">. Renvoie (formulaires POST, formulaires modifiés)."""
    texte = fichier.texte
    total = ajoutes = 0
    resultat, position = [], 0
    for m in FORMULAIRE_POST.finditer(texte):
        total += 1
        resultat.append(texte[position:m.end()])
        position = m.end()
        if "csrf_token" in texte[m.end():m.end() + 300]:
            continue
        debut_ligne = texte.rfind("\n", 0, m.start()) + 1
        indentation = re.match(r"[ \t]*", texte[debut_ligne:m.start()]).group(0)
        resultat.append("\n" + indentation + "  " + JETON)
        ajoutes += 1
    resultat.append(texte[position:])
    fichier.texte = "".join(resultat)
    return total, ajoutes


def main():
    for chemin in ("app.py", "templates"):
        if not os.path.exists(chemin):
            print(f"Introuvable : {chemin}. Lance ce programme depuis le dossier backend.")
            sys.exit(1)

    fichiers = []
    avertissements = []

    # ---------------------------------------------------------- 1. app.py
    app_py = Fichier("app.py")
    if "CSRFProtect" in app_py.texte:
        print("[OK ] app.py : la protection CSRF est déjà installée")
    else:
        app_py.une_fois("import de Flask-WTF", "from dotenv import load_dotenv\n",
                        "from dotenv import load_dotenv\nfrom flask_wtf.csrf import CSRFProtect, CSRFError\n")
        app_py.une_fois("durée du jeton (valable autant que la session)",
                        "app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)\n",
                        "app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)\n"
                        "app.config['WTF_CSRF_TIME_LIMIT'] = None\n")
        app_py.une_fois("activation de la protection sur toutes les routes", "db.init_app(app)\n", "db.init_app(app)\n" + BLOC_INIT)
    app_py.une_fois("/refuser : POST seulement, et fonction désactivée par défaut",
                    '@app.route("/dossiers/<int:dossier_id>/refuser")\ndef refuser_devis(dossier_id):\n',
                    '@app.route("/dossiers/<int:dossier_id>/refuser", methods=["POST"])\ndef refuser_devis(dossier_id):\n'
                    '    if not AFFICHER_FONCTIONNALITES_MASQUEES:\n        abort(404)\n',
                    obligatoire=False)
    fichiers.append(app_py)

    # ---------------------------------------------------------- 2. templates
    total_forms = total_ajoutes = 0
    detail = []
    for chemin in sorted(glob.glob("templates/*.html")):
        f = Fichier(chemin)
        n, a = proteger_formulaires(f)
        if n:
            detail.append((chemin, n, a))
            total_forms += n
            total_ajoutes += a
            if f.modifie():
                fichiers.append(f)
        for m in FORMULAIRE_TOUS.finditer(f.original):
            balise = m.group(0)
            if not FORMULAIRE_POST.match(balise) and re.search(r"method\s*=\s*[\"']?\{", balise, re.I):
                avertissements.append(f"{chemin} : formulaire à méthode variable, à vérifier à la main : {balise[:80]}")
        for motif in (r"fetch\(", r"XMLHttpRequest", r"\.submit\(\)", r"createElement\(['\"]form"):
            if re.search(motif, f.original):
                avertissements.append(f"{chemin} : contient « {motif.replace(chr(92), '')} » : si cela envoie des données, ajouter l'en-tête X-CSRFToken")
        if re.search(r'href="[^"]*/refuser', f.original):
            avertissements.append(f"{chemin} : lien vers /refuser : il doit devenir un formulaire POST avec jeton (la route n'accepte plus GET)")
    for chemin, n, a in detail:
        print(f"[OK ] {chemin} : {n} formulaire(s) POST, {a} jeton(s) ajouté(s)")
    print(f"      Total : {total_forms} formulaires POST, {total_ajoutes} jeton(s) ajouté(s)")

    # ---------------------------------------------------------- 3. assistant.py
    if os.path.exists("assistant.py"):
        a = Fichier("assistant.py")
        if "generate_csrf" in a.texte:
            print("[OK ] assistant.py : le jeton est déjà envoyé")
        else:
            a.une_fois("import du générateur de jeton", "from markupsafe import Markup\n",
                       "from markupsafe import Markup\nfrom flask_wtf.csrf import generate_csrf\n")
            a.une_fois("l'assistant envoie le jeton dans l'en-tête X-CSRFToken",
                       "headers: { 'Content-Type': 'application/json' },",
                       "headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '__CSRF__' },")
            a.une_fois("le jeton est inséré dans la page", "return Markup(WIDGET_HTML)",
                       'return Markup(WIDGET_HTML.replace("__CSRF__", generate_csrf()))')
            fichiers.append(a)
    else:
        print("[-- ] assistant.py : absent, rien à faire")

    # ---------------------------------------------------------- 4. requirements.txt
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", encoding="utf-8") as f:
            contenu = f.read()
        if re.search(r"^flask-wtf\b", contenu, re.I | re.M):
            print("[OK ] requirements.txt : Flask-WTF est déjà listé")
        else:
            r = Fichier("requirements.txt")
            r.texte = r.texte.rstrip("\n") + "\nFlask-WTF\n"
            fichiers.append(r)
            print("[OK ] requirements.txt : Flask-WTF ajouté")
    else:
        avertissements.append("requirements.txt introuvable dans backend : ajoute la ligne Flask-WTF dans ton fichier de dépendances")

    problemes = [p for f in fichiers for p in f.problemes]
    if problemes:
        print("\nRIEN n'a été modifié. Envoie-moi ces lignes et colle-moi le fichier concerné :")
        for p in problemes:
            print("  -", p)
        sys.exit(1)

    # ---------------------------------------------------------- écriture
    ecrits = []
    for f in fichiers:
        if f.modifie():
            shutil.copyfile(f.chemin, f.chemin + ".avant-csrf")
            with open(f.chemin, "w", encoding="utf-8", newline="") as sortie:
                sortie.write(f.texte)
            ecrits.append(f.chemin)
    if not os.path.exists("templates/session_expiree.html"):
        with open("templates/session_expiree.html", "w", encoding="utf-8", newline="") as sortie:
            sortie.write(PAGE_SESSION_EXPIREE)
        ecrits.append("templates/session_expiree.html (nouveau)")

    print("\nTERMINÉ." if ecrits else "\nRien à modifier : tout est déjà en place.")
    for chemin in ecrits:
        print("  -", chemin)
    if avertissements:
        print("\nÀ VÉRIFIER À LA MAIN :")
        for t in avertissements:
            print("  *", t)
    print("\nÉtape suivante : relance le site (Ctrl+C, puis python app.py), puis lance :   python verifier_csrf.py")


main()