"""
Met en place les 3 espaces de produits : Particuliers, Professionnels, Dirigeants.
  1. la base de données : 12 nouveaux produits, colonnes espace / photo / ordre ;
  2. le code : models.py, app.py, liste_produits.html, produit.html, base.html, accueil.html.
A lancer UNE SEULE FOIS, dans le dossier backend :   python appliquer_produits.py
Avant toute modification, chaque fichier est copié en "nom.avant-produits".
Si une ligne attendue n'est pas trouvée, RIEN n'est modifié (ni la base, ni les fichiers).
"""
import json
import re
import shutil
import sys

from sqlalchemy import text

# Les 6 produits qui existent déjà : (nom actuel, nouveau nom ou None, espace, photo, ordre)
EXISTANTS = [
    ("Mutuelle santé particuliers", None, "Particuliers", "sante.jpg", 1),
    ("Mutuelle santé seniors", None, "Particuliers", "senior.jpg", 2),
    ("Assurance emprunteur", None, "Particuliers", "ass-emp.jpg", 4),
    ("Plan Épargne Retraite", "Plan Épargne Retraite (PER)", "Particuliers", "per.jpg", 5),
    ("Mutuelle santé TNS", "Mutuelle TNS", "Dirigeants", "sante.jpg", 1),
    ("Prévoyance TNS", None, "Dirigeants", "prevoyance.jpg", 2),
]

# Les 12 nouveaux produits (textes provisoires, à faire valider par la direction)
NOUVEAUX = [
    ("Prévoyance", "Prévoyance", "Particuliers", "prevoyance.jpg", 3,
     "Protégez vos proches et vos revenus en cas d’accident de la vie, d’invalidité ou de décès.",
     "La prévoyance verse un capital ou une rente quand un événement grave vous empêche de travailler, ou en cas de décès, pour aider votre famille à garder son niveau de vie. Les garanties et leur montant varient selon le contrat choisi.",
     ["Décès : capital ou rente pour vos proches", "Invalidité", "Incapacité de travail", "Accidents de la vie", "Garanties adaptées à votre situation familiale"]),
    ("Habitation", "Habitation", "Particuliers", "particulier.jpg", 6,
     "Assurez votre logement, que vous soyez locataire ou propriétaire.",
     "L’assurance habitation protège votre logement et vos biens contre les dégâts du quotidien, et couvre votre responsabilité si vous causez un dommage à autrui. Les garanties dépendent de votre situation et du contrat choisi.",
     ["Incendie et explosion", "Dégâts des eaux", "Vol et vandalisme", "Catastrophes naturelles et événements climatiques", "Responsabilité civile", "Assistance en cas de sinistre"]),
    ("Automobile", "Automobile", "Particuliers", "particulier.jpg", 7,
     "Une assurance auto adaptée à votre véhicule et à votre façon de conduire.",
     "L’assurance auto couvre les dommages que vous pouvez causer aux autres (responsabilité civile, obligatoire) et peut protéger votre propre véhicule selon la formule choisie. Un conseiller compare les offres pour trouver la formule adaptée.",
     ["Responsabilité civile (obligatoire)", "Formules au tiers ou tous risques", "Vol et incendie", "Bris de glace", "Assistance et dépannage", "Protection du conducteur"]),
    ("Mutuelle (collectif)", "Santé", "Professionnels", "sante.jpg", 1,
     "Une complémentaire santé pour vos salariés, adaptée à votre entreprise.",
     "La mutuelle collective couvre les frais de santé de vos salariés en complément de l’Assurance Maladie. Le niveau de garanties et la répartition de la cotisation se définissent avec vous, selon votre convention collective et votre budget.",
     ["Soins courants et hospitalisation", "Optique, dentaire et audiologie", "Niveaux de garanties adaptés à vos équipes", "Prise en compte de votre convention collective", "Gestion simplifiée pour l’entreprise"]),
    ("Prévoyance (collectif)", "Prévoyance", "Professionnels", "prevoyance.jpg", 2,
     "Protégez vos salariés en cas d’arrêt de travail, d’invalidité ou de décès.",
     "La prévoyance collective garantit à vos salariés un revenu ou un capital en cas de coup dur, et protège leurs proches. Les garanties se définissent avec vous, selon votre activité et votre convention collective.",
     ["Incapacité temporaire de travail", "Invalidité", "Décès : capital ou rente", "Rente éducation et protection des proches", "Garanties adaptées à votre convention collective"]),
    ("Assurance emprunteur", "Emprunteur", "Professionnels", "ass-emp.jpg", 3,
     "Sécurisez le financement de votre projet professionnel avec une couverture adaptée.",
     "L’assurance emprunteur protège le remboursement d’un prêt professionnel en cas de décès, d’invalidité ou d’arrêt de travail de l’emprunteur. Un conseiller compare les offres de ses partenaires selon votre projet.",
     ["Décès", "Perte totale et irréversible d’autonomie", "Invalidité", "Incapacité temporaire de travail", "Couverture adaptée à la nature du prêt"]),
    ("Multirisque professionnel", "Multirisque", "Professionnels", "profe.jpg", 4,
     "Protégez vos locaux, votre matériel et votre activité contre les aléas du quotidien.",
     "Le multirisque professionnel réunit dans un seul contrat les principales garanties utiles à votre entreprise : dommages aux biens, responsabilité et pertes financières liées à un sinistre. Il se compose selon votre activité.",
     ["Incendie, dégâts des eaux, tempête", "Vol et vandalisme", "Bris de machines et matériel informatique", "Perte d’exploitation", "Responsabilité civile liée à l’exploitation", "Assistance en cas de sinistre"]),
    ("Responsabilité civile professionnelle", "Responsabilité civile", "Professionnels", "profe.jpg", 5,
     "Couvrez les dommages que votre activité peut causer à des tiers.",
     "La responsabilité civile professionnelle prend en charge les conséquences financières des dommages causés à un client ou à un tiers dans le cadre de votre activité. Elle est obligatoire pour certaines professions.",
     ["Dommages corporels, matériels et immatériels causés aux tiers", "Frais de défense en cas de litige", "Adaptation à votre secteur d’activité", "Options selon votre profession"]),
    ("Assurance automobile", "Automobile", "Professionnels", "profe.jpg", 6,
     "Assurez les véhicules de votre entreprise, du véhicule unique à la flotte.",
     "L’assurance automobile professionnelle couvre les véhicules utilisés pour votre activité et leurs conducteurs. Les garanties se choisissent selon l’usage des véhicules, leur nombre et votre activité.",
     ["Responsabilité civile (obligatoire)", "Dommages au véhicule selon la formule", "Vol et incendie", "Assistance et dépannage", "Solutions pour une flotte de véhicules", "Protection du conducteur"]),
    ("Assurance PNO professionnelle", "PNO", "Professionnels", "profe.jpg", 7,
     "Protégez un local professionnel dont vous êtes propriétaire sans l’occuper.",
     "L’assurance propriétaire non occupant (PNO) protège un local professionnel que vous possédez et qui est loué ou vacant : dommages au bâtiment et responsabilité du propriétaire. Elle complète l’assurance de votre locataire.",
     ["Incendie et explosion", "Dégâts des eaux", "Événements climatiques et catastrophes naturelles", "Responsabilité civile du propriétaire", "Recours des voisins et des tiers", "Local vacant ou loué"]),
    ("Complémentaire retraite / PER", "Retraite", "Dirigeants", "per.jpg", 3,
     "Préparez votre retraite de dirigeant avec une solution fiscalement avantageuse.",
     "La retraite obligatoire d’un dirigeant ou d’un indépendant ne suffit pas toujours à maintenir son niveau de vie. Le PER permet de se constituer une épargne retraite avec un cadre fiscal avantageux, sous conditions. Un conseiller étudie avec vous la solution adaptée à votre situation.",
     ["Versements libres ou programmés", "Cadre fiscal avantageux, sous conditions", "Sortie en capital ou en rente selon le contrat", "Possibilité de transférer un contrat existant", "Accompagnement dans le choix du support"]),
    ("Assurance Homme clé", "Homme clé", "Dirigeants", "profe.jpg", 4,
     "Protégez votre entreprise si une personne indispensable ne peut plus travailler.",
     "L’assurance homme clé protège l’entreprise contre les conséquences financières du décès, de l’invalidité ou de l’arrêt de travail d’une personne dont l’activité est déterminante : dirigeant, associé ou collaborateur essentiel. L’indemnité est versée à l’entreprise.",
     ["Décès de la personne clé", "Invalidité", "Incapacité temporaire de travail", "Capital versé à l’entreprise pour faire face à la perte", "Contrat adapté à la taille et à l’activité de l’entreprise"]),
]

# ---------------------------------------------------------------------------
# Les modifications du code
# ---------------------------------------------------------------------------

FICHE_ANCIENNE = '''@app.route("/produits/<int:produit_id>")
def fiche_produit(produit_id):
    produit = Produit.query.get_or_404(produit_id)
    return render_template("produit.html", produit=produit)
'''

FICHE_NOUVELLE = '''@app.route("/dirigeants")
def page_dirigeants():
    produits = Produit.query.filter_by(espace="Dirigeants").order_by(Produit.ordre, Produit.id).all()
    return render_template(
        "liste_produits.html",
        produits=produits,
        titre="Dirigeants",
        sous_titre="Nos solutions pour les dirigeants d'entreprise.",
        vers_devis=False
    )


@app.route("/produits/<int:produit_id>")
def fiche_produit(produit_id):
    produit = Produit.query.get_or_404(produit_id)
    if produit.espace is None:
        abort(404)
    return render_template("produit.html", produit=produit)
'''

CARTE_DIRIGEANTS = '''
      <article class="acc-espace">
        <img src="{{ url_for('static', filename='diri.jpg') }}" alt="">
        <div class="acc-espace-corps">
          <h3>Dirigeants</h3>
          <p>Mutuelle et prévoyance TNS, retraite, assurance homme clé : protégez-vous et protégez votre entreprise.</p>
          <div><a href="/dirigeants" class="acc-btn acc-btn-bleu">Voir les produits Dirigeants</a></div>
        </div>
      </article>'''

BOUTONS_AUTRES_ESPACES = """{% for nom_espace, adresse in [('Particuliers', '/particuliers'), ('Professionnels', '/professionnels'), ('Dirigeants', '/dirigeants')] %}
    {% if est_espace and titre != nom_espace %}
    <a href="{{ adresse }}" class="acc-btn acc-btn-ligne">Voir les produits {{ nom_espace }}</a>
    {% endif %}
    {% endfor %}"""


class Fichier:
    def __init__(self, chemin):
        self.chemin = chemin
        with open(chemin, encoding="utf-8") as f:
            self.texte = f.read()
        self.problemes = []

    def _appliquer(self, etiquette, trouve, attendu, optionnel, faire):
        if trouve == attendu:
            self.texte = faire()
            print(f"[OK ] {self.chemin} : {etiquette}")
        elif optionnel:
            print(f"[-- ] {self.chemin} : {etiquette} : non trouvé (facultatif, laissé tel quel)")
        else:
            print(f"[PROBLEME] {self.chemin} : {etiquette} : trouvé {trouve} fois, attendu {attendu}")
            self.problemes.append(f"{self.chemin} : {etiquette}")

    def remplacer(self, etiquette, ancien, nouveau, attendu=1, optionnel=False):
        self._appliquer(etiquette, self.texte.count(ancien), attendu, optionnel,
                        lambda: self.texte.replace(ancien, nouveau))

    def regex(self, etiquette, motif, nouveau, attendu=1, optionnel=False, flags=0):
        remplacement = nouveau if callable(nouveau) else (lambda m: nouveau)
        self._appliquer(etiquette, len(re.findall(motif, self.texte, flags)), attendu, optionnel,
                        lambda: re.sub(motif, remplacement, self.texte, flags=flags))

    def verifier_absent(self, etiquette, mot):
        if mot in self.texte:
            print(f"[PROBLEME] {self.chemin} : {etiquette}")
            self.problemes.append(f"{self.chemin} : {etiquette}")


def preparer_code():
    models = Fichier("models.py")
    models.remplacer("3 colonnes du produit (espace, photo, ordre)",
                     "    formulaire_schema = db.Column(db.JSON)\n",
                     "    formulaire_schema = db.Column(db.JSON)\n    espace = db.Column(db.String(30))\n"
                     "    photo = db.Column(db.String(100))\n    ordre = db.Column(db.Integer)\n")

    app_py = Fichier("app.py")
    app_py.remplacer("page Particuliers",
                     "Produit.query.filter(Produit.categorie.in_(CATEGORIES_PARTICULIERS)).all()",
                     'Produit.query.filter_by(espace="Particuliers").order_by(Produit.ordre, Produit.id).all()')
    app_py.remplacer("page Professionnels",
                     "Produit.query.filter(Produit.categorie.in_(CATEGORIES_PROFESSIONNELS)).all()",
                     'Produit.query.filter_by(espace="Professionnels").order_by(Produit.ordre, Produit.id).all()')
    app_py.remplacer("nouvelle page Dirigeants et fiche produit", FICHE_ANCIENNE, FICHE_NOUVELLE)
    app_py.remplacer("plan du site : page Dirigeants",
                     '"/professionnels", "/contact-info",', '"/professionnels", "/dirigeants", "/contact-info",')
    app_py.remplacer("plan du site : produits affichés seulement",
                     'for p in Produit.query.all()]', 'for p in Produit.query.filter(Produit.espace.isnot(None)).all()]')

    liste = Fichier("templates/liste_produits.html")
    liste.regex("fin de la liste des photos dans le fichier", r"\{% set images = \{.*?\} %\}\n", "", flags=re.S)
    liste.remplacer("espaces reconnus", "titre in ['Particuliers', 'Professionnels']",
                    "titre in ['Particuliers', 'Professionnels', 'Dirigeants']")
    liste.remplacer("onglet Dirigeants",
                    '''<li><a href="/professionnels"{% if titre == 'Professionnels' %} aria-current="page"{% endif %}>Professionnels</a></li>''',
                    '''<li><a href="/professionnels"{% if titre == 'Professionnels' %} aria-current="page"{% endif %}>Professionnels</a></li>
      <li><a href="/dirigeants"{% if titre == 'Dirigeants' %} aria-current="page"{% endif %}>Dirigeants</a></li>''')
    liste.regex("photo lue dans la base", r"images\.get\(produit\.nom,\s*'[^']*'\)", "(produit.photo or 'diri.jpg')")
    liste.regex("boutons vers les deux autres espaces",
                r"\{% if titre == 'Particuliers' %\}\s*<a href=\"/professionnels\" class=\"acc-btn acc-btn-ligne\">.*?\{% endif %\}",
                BOUTONS_AUTRES_ESPACES, flags=re.S)
    liste.verifier_absent("il reste une référence à « images »", "images.get")

    produit = Fichier("templates/produit.html")
    produit.regex("fin de la liste des photos dans le fichier", r"\{% set images = \{.*?\} %\}\n", "", flags=re.S)
    produit.regex("espace lu dans la base",
                  r"\{% set est_pro = [^\n]*\n\{% set espace = [^\n]*\n\{% set espace_url = [^\n]*",
                  "{% set espace = produit.espace or 'Particuliers' %}\n{% set espace_url = '/' ~ (espace|lower) %}")
    produit.regex("photo lue dans la base", r"images\.get\(produit\.nom,\s*'[^']*'\)", "(produit.photo or 'particulier.jpg')")
    produit.verifier_absent("il reste une référence à « est_pro »", "est_pro")
    produit.verifier_absent("il reste une référence à « images »", "images.get")

    base = Fichier("templates/base.html")
    base.regex("lien Dirigeants dans le menu", r'<a href="/professionnels"[^\n]*>Professionnels</a>',
               lambda m: m.group(0) + '''\n    <a href="/dirigeants"{% if chemin == '/dirigeants' %} aria-current="page"{% endif %}>Dirigeants</a>''')

    accueil = Fichier("templates/accueil.html")
    accueil.remplacer("3 cartes sur une ligne",
                      ".acc-espaces { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }",
                      ".acc-espaces { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; }")
    accueil.regex("carte Dirigeants",
                  r'<div><a href="/professionnels" class="acc-btn acc-btn-bleu">Voir les produits Professionnels</a></div>\n\s*</div>\n\s*</article>',
                  lambda m: m.group(0) + CARTE_DIRIGEANTS)
    accueil.remplacer("texte de la carte Particuliers",
                      "Mutuelle santé, offre pour les seniors, assurance emprunteur, épargne retraite : des garanties pensées pour vous et vos proches.",
                      "Mutuelle santé, prévoyance, assurance emprunteur, retraite, habitation, automobile : des garanties pensées pour vous et vos proches.",
                      optionnel=True)
    accueil.remplacer("texte de la carte Professionnels",
                      "Mutuelle santé et prévoyance pour les indépendants, assurance emprunteur : protégez votre activité et vos revenus.",
                      "Mutuelle et prévoyance collectives, multirisque, responsabilité civile, automobile : protégez votre entreprise et vos salariés.",
                      optionnel=True)
    return [models, app_py, liste, produit, base, accueil]


# ---------------------------------------------------------------------------
# La base de données
# ---------------------------------------------------------------------------

def reorganiser_base():
    from app import app, db

    with app.app_context():
        session = db.session
        colonnes = {ligne[0] for ligne in session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'produits'"))}

        if "espace" in colonnes:
            deja = session.execute(text("SELECT COUNT(*) FROM produits WHERE espace IS NOT NULL")).scalar()
            if deja:
                print("[OK ] base de données : produits déjà réorganisés, rien à faire")
                return

        problemes = []
        for nom, *_ in EXISTANTS:
            n = session.execute(text("SELECT COUNT(*) FROM produits WHERE nom = :nom"), {"nom": nom}).scalar()
            print(f"[{'OK ' if n == 1 else 'PROBLEME'}] base de données : produit « {nom} » trouvé {n} fois (attendu 1)")
            if n != 1:
                problemes.append(nom)
        if problemes:
            print("\nRIEN n'a été modifié. Envoie-moi ces lignes, et le résultat de : SELECT id, nom FROM produits;")
            sys.exit(1)

        session.execute(text("CREATE TABLE IF NOT EXISTS sauvegarde_produits AS SELECT * FROM produits"))
        for colonne, definition in (("espace", "VARCHAR(30) NULL"), ("photo", "VARCHAR(100) NULL"), ("ordre", "INT NULL")):
            if colonne not in colonnes:
                session.execute(text(f"ALTER TABLE produits ADD COLUMN {colonne} {definition}"))
        session.commit()

        try:
            for nom, nouveau_nom, espace, photo, ordre in EXISTANTS:
                session.execute(
                    text("UPDATE produits SET nom = :nouveau, espace = :espace, photo = :photo, ordre = :ordre WHERE nom = :nom"),
                    {"nouveau": nouveau_nom or nom, "espace": espace, "photo": photo, "ordre": ordre, "nom": nom})
            for nom, categorie, espace, photo, ordre, description, presentation, garanties in NOUVEAUX:
                session.execute(
                    text("INSERT INTO produits (nom, categorie, espace, photo, ordre, description, presentation, garanties) "
                         "VALUES (:nom, :categorie, :espace, :photo, :ordre, :description, :presentation, :garanties)"),
                    {"nom": nom, "categorie": categorie, "espace": espace, "photo": photo, "ordre": ordre,
                     "description": description, "presentation": presentation,
                     "garanties": json.dumps(garanties, ensure_ascii=False)})
            session.commit()
        except Exception:
            session.rollback()
            print("\nUne erreur est survenue : rien n'a été modifié dans les produits.")
            raise

        total = session.execute(text("SELECT COUNT(*) FROM produits WHERE espace IS NOT NULL")).scalar()
        print(f"[OK ] base de données : {total} produits répartis en 3 espaces (copie des anciens : table sauvegarde_produits)")


def main():
    try:
        with open("models.py", encoding="utf-8") as f:
            code_deja_fait = "espace = db.Column" in f.read()
    except FileNotFoundError:
        print("models.py est introuvable : lance ce programme depuis le dossier backend.")
        sys.exit(1)

    fichiers = []
    if code_deja_fait:
        print("[OK ] code : déjà à jour (models.py contient déjà la colonne espace)")
    else:
        try:
            fichiers = preparer_code()
        except FileNotFoundError as erreur:
            print(f"Fichier introuvable : {erreur.filename}. Lance ce programme depuis le dossier backend.")
            sys.exit(1)
        problemes = [p for f in fichiers for p in f.problemes]
        if problemes:
            print("\nRIEN n'a été modifié (ni la base, ni les fichiers). Envoie-moi ces lignes :")
            for p in problemes:
                print("  -", p)
            print("et colle-moi le fichier concerné.")
            sys.exit(1)

    reorganiser_base()

    if fichiers:
        for f in fichiers:
            shutil.copyfile(f.chemin, f.chemin + ".avant-produits")
            with open(f.chemin, "w", encoding="utf-8", newline="") as sortie:
                sortie.write(f.texte)
        print("\nTERMINÉ.")
        print("Fichiers modifiés (chaque ancienne version est gardée en « nom.avant-produits ») :")
        for f in fichiers:
            print("  -", f.chemin)
    print("\nÉtape suivante : relance le site (Ctrl+C puis python app.py).")


main()