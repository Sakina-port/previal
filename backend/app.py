from flask import Flask, render_template, request, redirect, abort, Response, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import os
import secrets
import bcrypt
import base64
import uuid
import hashlib
import filetype
import csv
import io
import json
import zipfile
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from weasyprint import HTML
from sqlalchemy import or_, exists, and_
from models import db, Produit, Dossier, Devis, Contrat, Signature, Utilisateur, Historique, Note, DemandeDocuments, Document, Rappel, EtudePartenaire, JournalConnexion
from moteur_devis import obtenir_devis
from mailer import configurer_mail, envoyer_documents, envoyer_accuse_reception, notifier_equipe_nouvelle_demande, envoyer_demande_documents, notifier_equipe_depot
from stockage import enregistrer_fichier, lire_fichier, supprimer_fichier, StockageErreur, existe_dans_bucket, adresse_temporaire

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-moi-plus-tard')
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
AFFICHER_FONCTIONNALITES_MASQUEES = os.getenv('AFFICHER_FONCTIONNALITES_MASQUEES', 'False') == 'True'
db.init_app(app)
configurer_mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "compte"


@app.before_request
def session_avec_expiration():
    session.permanent = True


@login_manager.unauthorized_handler
def non_connecte():
    if request.path.startswith("/equipe"):
        return redirect("/equipe")
    return redirect("/compte")


STATUTS = [
    ("nouveau", "Nouveau"),
    ("a_contacter", "À contacter"),
    ("contacte", "Contacté"),
    ("besoin_a_analyser", "Besoin à analyser"),
    ("en_attente_de_pieces", "En attente de pièces"),
    ("devis_en_cours", "Devis en cours"),
    ("proposition_envoyee", "Proposition envoyée"),
    ("souscription_en_cours", "Souscription en cours"),
    ("client", "Client"),
    ("sans_suite", "Sans suite"),
]

PIECES = [
    ("piece_identite", "Pièce d'identité"),
    ("rib", "RIB"),
    ("justificatif_domicile", "Justificatif de domicile"),
    ("devis_existant", "Devis existant"),
    ("document_contractuel", "Document contractuel"),
    ("autre_piece", "Autre pièce autorisée"),
]

PARTENAIRES = ["SPVIE", "Kereis", "Autre"]
CATEGORIES_DEVIS = {f"devis_{p.lower()}": f"Devis {p}" for p in PARTENAIRES}

ETATS_ETUDE = [
    ("a_interroger", "À interroger"),
    ("demande", "Demandé"),
    ("reponse_recue", "Réponse reçue"),
    ("propose", "Proposé au client"),
    ("sans_suite", "Sans suite"),
]

DUREE_LIEN_HEURES = 48

TYPES_AUTORISES = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}
TAILLE_MAX_FICHIER = 10 * 1024 * 1024
ROLES_EQUIPE = ("admin", "gestionnaire")
DUREE_CONSERVATION_MOIS = 36
CRENEAUX = [f"{h}h30 - {h + 1}h30" for h in range(9, 17)]
SITUATIONS = ["Célibataire", "Marié(e)", "Pacsé(e)", "Union libre", "Divorcé(e)", "Veuf(ve)"]
CATEGORIES_PARTICULIERS = ["Santé", "Retraite", "Emprunteur"]
CATEGORIES_PROFESSIONNELS = ["Santé TNS", "Prévoyance TNS", "Emprunteur"]
AFFICHER_ESPACE_CLIENT = os.getenv('AFFICHER_ESPACE_CLIENT', 'False') == 'True'


@app.context_processor
def droits_pour_templates():
    return {
        "est_admin": current_user.is_authenticated and current_user.role == "admin",
        "creneaux": CRENEAUX,
        "situations": SITUATIONS,
        "afficher_espace_client": AFFICHER_ESPACE_CLIENT
    }


@app.template_filter("heure_paris")
def heure_paris(valeur, format="%d/%m/%Y %H:%M"):
    if valeur is None:
        return ""
    return valeur.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Paris")).strftime(format)


@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))


@app.route("/")
def accueil():
    produits = Produit.query.all()
    return render_template("accueil.html", produits=produits, numero_dossier=None)


@app.route("/catalogue")
def catalogue():
    produits = Produit.query.all()
    return render_template("catalogue.html", produits=produits)


@app.route("/devis")
def devis_choix():
    produits = Produit.query.all()
    return render_template(
        "liste_produits.html",
        produits=produits,
        titre="Obtenir un devis",
        sous_titre="Choisissez le produit qui vous intéresse pour démarrer votre demande.",
        vers_devis=True
    )


@app.route("/particuliers")
def page_particuliers():
    produits = Produit.query.filter(Produit.categorie.in_(CATEGORIES_PARTICULIERS)).all()
    return render_template(
        "liste_produits.html",
        produits=produits,
        titre="Particuliers",
        sous_titre="Nos solutions pour vous et vos proches.",
        vers_devis=False
    )


@app.route("/professionnels")
def page_professionnels():
    produits = Produit.query.filter(Produit.categorie.in_(CATEGORIES_PROFESSIONNELS)).all()
    return render_template(
        "liste_produits.html",
        produits=produits,
        titre="Professionnels",
        sous_titre="Nos solutions pour les indépendants et les entreprises.",
        vers_devis=False
    )


@app.route("/produits/<int:produit_id>")
def fiche_produit(produit_id):
    produit = Produit.query.get_or_404(produit_id)
    return render_template("produit.html", produit=produit)


@app.route("/produits/<int:produit_id>/devis", methods=["GET", "POST"])
def formulaire(produit_id):
    if not AFFICHER_FONCTIONNALITES_MASQUEES:
        abort(404)
    produit = Produit.query.get_or_404(produit_id)

    if request.method == "POST":
        reponses = {}
        for champ in produit.formulaire_schema["champs"]:
            reponses[champ["nom"]] = request.form.get(champ["nom"])

        nouveau_dossier = Dossier(
            produit_id=produit.id,
            statut="en_cours",
            source="interne",
            reponses=reponses
        )
        db.session.add(nouveau_dossier)
        db.session.commit()

        resultat = obtenir_devis(produit, reponses)
        nouveau_devis = Devis(
            dossier_id=nouveau_dossier.id,
            montant=resultat["prix"],
            provider=resultat["provider"]
        )
        db.session.add(nouveau_devis)
        db.session.commit()

        return render_template("devis_resultat.html", produit=produit, devis=nouveau_devis, dossier=nouveau_dossier)

    return render_template("formulaire.html", produit=produit)


@app.route("/dossiers/<int:dossier_id>/refuser")
def refuser_devis(dossier_id):
    dossier = Dossier.query.get_or_404(dossier_id)
    dossier.statut = "refuse"
    db.session.commit()
    return redirect("/catalogue")


@app.route("/dossiers/<int:dossier_id>/signature", methods=["GET", "POST"])
def signature(dossier_id):
    if not AFFICHER_FONCTIONNALITES_MASQUEES:
        abort(404)
    dossier = Dossier.query.get_or_404(dossier_id)
    produit = Produit.query.get(dossier.produit_id)
    devis = Devis.query.filter_by(dossier_id=dossier.id).first()

    if request.method == "POST":
        dossier.statut = "accepte"

        dossier_documents = os.path.join("static", "documents")
        os.makedirs(dossier_documents, exist_ok=True)

        signature_data = request.form.get("signature_data")
        nom_fichier_signature = f"signature_dossier_{dossier.id}.png"
        chemin_signature = os.path.join(dossier_documents, nom_fichier_signature)

        image_base64 = signature_data.split(",")[1]
        with open(chemin_signature, "wb") as f:
            f.write(base64.b64decode(image_base64))

        nouvelle_signature = Signature(
            dossier_id=dossier.id,
            statut="signe",
            provider="interne",
            fichier_signature=f"documents/{nom_fichier_signature}",
            date_signature=datetime.utcnow()
        )
        db.session.add(nouvelle_signature)
        db.session.commit()

        html_devis = render_template(
            "devis_pdf.html",
            produit=produit, dossier=dossier, devis=devis,
            date_du_jour=date.today().strftime("%d/%m/%Y")
        )
        nom_fichier_devis = f"devis_dossier_{dossier.id}.pdf"
        HTML(string=html_devis).write_pdf(os.path.join(dossier_documents, nom_fichier_devis))
        devis.fichier_pdf = f"documents/{nom_fichier_devis}"
        db.session.commit()

        html_contrat = render_template(
            "contrat_pdf.html",
            produit=produit, dossier=dossier, devis=devis,
            date_du_jour=date.today().strftime("%d/%m/%y"),
            signature_data=signature_data
        )
        nom_fichier_contrat = f"contrat_dossier_{dossier.id}.pdf"
        HTML(string=html_contrat).write_pdf(os.path.join(dossier_documents, nom_fichier_contrat))

        nouveau_contrat = Contrat(
            dossier_id=dossier.id,
            fichier_pdf=f"documents/{nom_fichier_contrat}",
            source="interne"
        )
        db.session.add(nouveau_contrat)
        db.session.commit()

        email_client = dossier.reponses.get("email", "non_renseigne@exemple.com")
        envoyer_documents(
             destinataire=email_client,
             produit_nom=produit.nom,
             dossier_id=dossier.id,
             chemin_devis=os.path.join(dossier_documents, nom_fichier_devis),
             chemin_contrat=os.path.join(dossier_documents, nom_fichier_contrat)
          )

        return render_template("devis_accepte.html", dossier=dossier, devis=devis, contrat=nouveau_contrat)

    return render_template("signature.html", produit=produit, devis=devis, dossier=dossier)


@app.route("/compte", methods=["GET", "POST"])
def compte():
    if not AFFICHER_ESPACE_CLIENT:
        abort(404)
    if request.method == "POST":
        email = request.form.get("email")
        mot_de_passe_tape = request.form.get("mot_de_passe")

        utilisateur = Utilisateur.query.filter_by(email=email).first()

        if utilisateur and bcrypt.checkpw(mot_de_passe_tape.encode('utf-8'), utilisateur.mot_de_passe.encode('utf-8')):
            login_user(utilisateur)
            return redirect("/espace-client")
        else:
            return render_template("compte.html", erreur="E-mail ou mot de passe incorrect.")

    return render_template("compte.html")


@app.route("/inscription", methods=["POST"])
def inscription():
    if not AFFICHER_ESPACE_CLIENT:
        abort(404)
    nom = request.form.get("nom")
    prenom = request.form.get("prenom")
    email = request.form.get("email")
    mot_de_passe_tape = request.form.get("mot_de_passe")

    existe_deja = Utilisateur.query.filter_by(email=email).first()
    if existe_deja:
        return render_template("compte.html", erreur="Cet e-mail est déjà utilisé.")

    hash_mot_de_passe = bcrypt.hashpw(mot_de_passe_tape.encode('utf-8'), bcrypt.gensalt())

    nouvel_utilisateur = Utilisateur(
        nom=nom,
        prenom=prenom,
        email=email,
        mot_de_passe=hash_mot_de_passe.decode('utf-8')
    )
    db.session.add(nouvel_utilisateur)
    db.session.commit()

    login_user(nouvel_utilisateur)
    return redirect("/espace-client")


@app.route("/espace-client")
@login_required
def espace_client():
    if not AFFICHER_ESPACE_CLIENT:
       abort(404)
    return render_template("espace_client.html")


@app.route("/deconnexion")
def deconnexion():
    etait_equipe = current_user.is_authenticated and current_user.role in ROLES_EQUIPE
    logout_user()
    return redirect("/equipe" if etait_equipe else "/")


@app.route("/equipe/deconnexion")
def equipe_deconnexion():
    logout_user()
    return redirect("/equipe")


def valider_formulaire(reponses):
    erreurs = []
    for cle in reponses:
        if isinstance(reponses[cle], str):
            reponses[cle] = reponses[cle].strip()

    if reponses["civilite"] not in ("Monsieur", "Madame"):
        erreurs.append("Civilité invalide.")
    if reponses["profil"] not in ("Particulier", "TNS", "Entreprise"):
        erreurs.append("Profil invalide.")
    if reponses["besoin"] not in ("Santé", "Prévoyance", "Santé + Prévoyance", "Autre"):
        erreurs.append("Besoin invalide.")
    if reponses["moyen_contact_prefere"] not in ("Téléphone", "E-mail"):
        erreurs.append("Moyen de contact invalide.")
    if reponses["creneau_souhaite"] not in CRENEAUX + ["", None]:
        erreurs.append("Créneau invalide.")
    if reponses["situation_matrimoniale"] not in SITUATIONS:
        erreurs.append("Situation matrimoniale invalide.")

    try:
        age = int(reponses["age"])
        if not 18 <= age <= 99:
            raise ValueError
        reponses["age"] = age
    except (TypeError, ValueError):
        erreurs.append("L'âge doit être compris entre 18 et 99 ans.")

    nombre_enfants = None
    try:
        nombre_enfants = int(reponses["nombre_enfants"])
        if not 0 <= nombre_enfants <= 15:
            raise ValueError
        reponses["nombre_enfants"] = nombre_enfants
    except (TypeError, ValueError):
        nombre_enfants = None
        erreurs.append("Le nombre d'enfants doit être compris entre 0 et 15.")

    if nombre_enfants is not None:
        if nombre_enfants >= 3:
            if reponses["famille_nombreuse"] not in ("Oui", "Non"):
                erreurs.append("Merci d'indiquer si vous êtes une famille nombreuse.")
        else:
            reponses["famille_nombreuse"] = ""

    if len(reponses["nom"]) > 100 or len(reponses["prenom"]) > 100:
        erreurs.append("Le nom et le prénom ne doivent pas dépasser 100 caractères.")

    telephone = re.sub(r"[ .\-()]", "", reponses["telephone"])
    if not re.fullmatch(r"\+?\d{8,15}", telephone):
        erreurs.append("Le numéro de téléphone n'est pas valide.")

    email = reponses["email"]
    if len(email) > 200 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        erreurs.append("L'adresse e-mail n'est pas valide.")

    if reponses["commentaire"] and len(reponses["commentaire"]) > 1000:
        erreurs.append("Le commentaire ne doit pas dépasser 1000 caractères.")

    return erreurs


@app.route("/contact", methods=["POST"])
def contact():
    reponses = {
        "civilite": request.form.get("civilite"),
        "nom": request.form.get("nom"),
        "prenom": request.form.get("prenom"),
        "telephone": request.form.get("telephone"),
        "email": request.form.get("email"),
        "age": request.form.get("age"),
        "situation_matrimoniale": request.form.get("situation_matrimoniale"),
        "nombre_enfants": request.form.get("nombre_enfants"),
        "famille_nombreuse": request.form.get("famille_nombreuse"),
        "profil": request.form.get("profil"),
        "besoin": request.form.get("besoin"),
        "moyen_contact_prefere": request.form.get("moyen_contact_prefere"),
        "creneau_souhaite": request.form.get("creneau_souhaite"),
        "commentaire": request.form.get("commentaire"),
    }

    champs_obligatoires = ["civilite", "nom", "prenom", "telephone", "email", "age",
                           "situation_matrimoniale", "nombre_enfants", "profil", "besoin"]
    consentement = request.form.get("rgpd") == "on"
    texte_consentement = "J'accepte que mes données soient utilisées par Prévial pour traiter ma demande."
    champ_manquant = False
    for champ in champs_obligatoires:
        if not reponses[champ]:
            champ_manquant = True

    if champ_manquant or not consentement:
        produits = Produit.query.all()
        if not consentement:
            message = "Merci d'accepter le traitement de vos données pour envoyer votre demande."
        else:
            message = "Merci de remplir tous les champs obligatoires avant d'envoyer votre demande."
        return render_template("accueil.html", produits=produits, numero_dossier=None, erreur_formulaire=message)

    erreurs = valider_formulaire(reponses)
    if erreurs:
        produits = Produit.query.all()
        return render_template("accueil.html", produits=produits, numero_dossier=None, erreur_formulaire=" ".join(erreurs))

    reponses["consentement_rgpd"] = True
    reponses["consentement_date"] = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M:%S")
    reponses["consentement_texte"] = texte_consentement

    nouveau_dossier = Dossier(
        statut="nouveau",
        source="interne",
        reponses=reponses
    )
    db.session.add(nouveau_dossier)
    db.session.commit()

    nouveau_dossier.numero_dossier = f"PRV-{date.today().year}-{nouveau_dossier.id:06d}"
    db.session.commit()

    db.session.add(Historique(
        dossier_id=nouveau_dossier.id,
        action="Demande reçue via le formulaire de contact"
    ))
    db.session.commit()

    envoyer_accuse_reception(reponses["email"], nouveau_dossier.numero_dossier)
    notifier_equipe_nouvelle_demande(
        nouveau_dossier.numero_dossier,
        reponses["besoin"],
        reponses["nom"],
        reponses["prenom"],
        reponses["commentaire"]
    )

    produits = Produit.query.all()
    return render_template("accueil.html", produits=produits, numero_dossier=nouveau_dossier.numero_dossier)


@app.route("/contact-info")
def contact_info():
    return render_template("contact_info.html")


@app.route("/mentions-legales")
def mentions_legales():
    return render_template("page_legale.html", titre="Mentions légales", page="mentions")


@app.route("/confidentialite")
def confidentialite():
    return render_template("page_legale.html", titre="Politique de confidentialité", page="confidentialite")


@app.route("/cookies")
def cookies():
    return render_template("page_legale.html", titre="Gestion des cookies", page="cookies")


@app.route("/robots.txt")
def robots_txt():
    contenu = (
        "User-agent: *\n"
        "Disallow: /equipe\n"
        "Disallow: /depot/\n"
        "Disallow: /compte\n"
        "Disallow: /espace-client\n"
        "Disallow: /devis\n"
        "Disallow: /dossiers/\n"
        "Disallow: /catalogue\n"
        f"Sitemap: {request.host_url}sitemap.xml\n"
    )
    return Response(contenu, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    adresses = ["/", "/particuliers", "/professionnels", "/contact-info",
                "/mentions-legales", "/confidentialite", "/cookies"]
    adresses += [f"/produits/{p.id}" for p in Produit.query.all()]

    lignes = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for a in adresses:
        lignes.append(f"  <url><loc>{request.host_url.rstrip('/')}{a}</loc></url>")
    lignes.append("</urlset>")
    return Response("\n".join(lignes), mimetype="application/xml")


@app.route("/equipe", methods=["GET", "POST"])
def equipe_connexion():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        mot_de_passe_tape = request.form.get("mot_de_passe", "")

        utilisateur = Utilisateur.query.filter_by(email=email).first()

        reussi = bool(
            utilisateur
            and utilisateur.role in ROLES_EQUIPE
            and bcrypt.checkpw(mot_de_passe_tape.encode('utf-8'), utilisateur.mot_de_passe.encode('utf-8'))
        )

        db.session.add(JournalConnexion(
            utilisateur_id=utilisateur.id if utilisateur else None,
            email_saisi=email[:200],
            succes=reussi,
            adresse_ip=(request.remote_addr or "")[:45]
        ))
        db.session.commit()

        if reussi:
            login_user(utilisateur)
            return redirect("/equipe/tableau-de-bord")
        else:
            return render_template("equipe_connexion.html", erreur="Identifiants incorrects ou accès non autorisé.")

    return render_template("equipe_connexion.html")


@app.route("/equipe/tableau-de-bord")
@login_required
def equipe_tableau_de_bord():
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    compteurs = []
    for valeur, libelle in STATUTS:
        nombre = Dossier.query.filter_by(statut=valeur, archive=False).count()
        compteurs.append({"valeur": valeur, "libelle": libelle, "nombre": nombre})

    derniers_dossiers = Dossier.query.filter_by(archive=False).order_by(Dossier.date_creation.desc()).limit(10).all()

    maintenant = datetime.utcnow()
    demain_paris = (datetime.now(ZoneInfo("Europe/Paris")) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    fin_aujourdhui = demain_paris.astimezone(timezone.utc).replace(tzinfo=None)

    rappels_a_traiter = Rappel.query.filter(
        Rappel.fait.is_(False),
        Rappel.date_rappel < fin_aujourdhui
    ).order_by(Rappel.date_rappel.asc()).all()

    a_faire = []
    for r in rappels_a_traiter:
        a_faire.append({
            "rappel": r,
            "dossier": Dossier.query.get(r.dossier_id),
            "en_retard": r.date_rappel < maintenant
        })

    return render_template(
        "equipe_tableau_de_bord.html",
        compteurs=compteurs,
        derniers_dossiers=derniers_dossiers,
        a_faire=a_faire
    )


@app.route("/equipe/journal-connexions")
@login_required
def equipe_journal_connexions():
    if current_user.role != "admin":
        abort(404)

    lignes = JournalConnexion.query.order_by(JournalConnexion.date_creation.desc()).limit(50).all()
    return render_template("equipe_journal_connexions.html", lignes=lignes)


@app.route("/equipe/dossiers-a-examiner")
@login_required
def equipe_dossiers_a_examiner():
    if current_user.role != "admin":
        abort(404)

    mois = request.args.get("mois", DUREE_CONSERVATION_MOIS, type=int)
    mois = max(0, min(mois, 240))
    limite = datetime.utcnow() - timedelta(days=30 * mois)

    dossiers = Dossier.query.filter(Dossier.date_creation < limite).order_by(Dossier.date_creation.asc()).all()
    return render_template(
        "equipe_dossiers_a_examiner.html",
        dossiers=dossiers,
        mois=mois,
        duree_par_defaut=DUREE_CONSERVATION_MOIS,
        libelles=dict(STATUTS)
    )


def pieces_manquantes(ids):
    manquantes = {}
    if not ids:
        return manquantes

    demandees = {}
    demandes = DemandeDocuments.query.filter(
        DemandeDocuments.dossier_id.in_(ids),
        DemandeDocuments.revoquee.is_(False)
    ).all()
    for dm in demandes:
        demandees.setdefault(dm.dossier_id, set()).update(dm.pieces or [])

    recues = {}
    documents = Document.query.filter(
        Document.dossier_id.in_(ids),
        Document.statut != "supprime"
    ).all()
    for doc in documents:
        recues.setdefault(doc.dossier_id, set()).add(doc.categorie)

    for dossier_id, pieces in demandees.items():
        restantes = pieces - recues.get(dossier_id, set())
        if restantes:
            manquantes[dossier_id] = [libelle for valeur, libelle in PIECES if valeur in restantes]

    return manquantes


@app.route("/equipe/dossiers")
@login_required
def equipe_dossiers():
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    page = request.args.get("page", 1, type=int)
    statut_filtre = request.args.get("statut", "")
    profil_filtre = request.args.get("profil", "")
    produit_filtre = request.args.get("produit", "")
    partenaire_filtre = request.args.get("partenaire", "")
    archives = request.args.get("archives", "")
    tri = request.args.get("tri", "recent")
    q = request.args.get("q", "").strip()
    du = request.args.get("du", "")
    au = request.args.get("au", "")

    requete = Dossier.query

    for mot in q.split():
        motif = f"%{mot}%"
        requete = requete.filter(or_(
            Dossier.numero_dossier.like(motif),
            Dossier.reponses["nom"].as_string().collate("utf8mb4_general_ci").like(motif),
            Dossier.reponses["prenom"].as_string().collate("utf8mb4_general_ci").like(motif),
            Dossier.reponses["email"].as_string().collate("utf8mb4_general_ci").like(motif),
            Dossier.reponses["telephone"].as_string().collate("utf8mb4_general_ci").like(motif),
        ))

    if statut_filtre:
        requete = requete.filter(Dossier.statut == statut_filtre)
    if profil_filtre:
        requete = requete.filter(Dossier.reponses["profil"].as_string() == profil_filtre)
    if produit_filtre:
        requete = requete.filter(Dossier.reponses["besoin"].as_string() == produit_filtre)
    if partenaire_filtre in PARTENAIRES:
        requete = requete.filter(exists().where(and_(
            EtudePartenaire.dossier_id == Dossier.id,
            EtudePartenaire.partenaire == partenaire_filtre
        )))

    if archives == "1":
        requete = requete.filter(Dossier.archive.is_(True))
    else:
        requete = requete.filter(Dossier.archive.is_(False))

    if du:
        try:
            debut = datetime.strptime(du, "%Y-%m-%d")
            requete = requete.filter(Dossier.date_creation >= debut)
        except ValueError:
            du = ""
    if au:
        try:
            fin = datetime.strptime(au, "%Y-%m-%d") + timedelta(days=1)
            requete = requete.filter(Dossier.date_creation < fin)
        except ValueError:
            au = ""

    if tri == "ancien":
        requete = requete.order_by(Dossier.date_creation.asc())
    elif tri == "nom":
        requete = requete.order_by(Dossier.reponses["nom"].as_string().asc())
    elif tri == "prenom":
        requete = requete.order_by(Dossier.reponses["prenom"].as_string().asc())
    elif tri == "email":
        requete = requete.order_by(Dossier.reponses["email"].as_string().asc())
    elif tri == "statut":
        requete = requete.order_by(Dossier.statut.asc())
    else:
        requete = requete.order_by(Dossier.date_creation.desc())

    dossiers = requete.paginate(page=page, per_page=10, error_out=False)

    ids = [d.id for d in dossiers.items]
    dernieres = {}
    if ids:
        lignes = Historique.query.filter(Historique.dossier_id.in_(ids)).order_by(Historique.date_creation.asc()).all()
        for h in lignes:
            dernieres[h.dossier_id] = h

    manquantes = pieces_manquantes(ids)

    return render_template(
        "equipe_dossiers.html",
        dossiers=dossiers,
        statuts=STATUTS,
        libelles=dict(STATUTS),
        statut_filtre=statut_filtre,
        profil_filtre=profil_filtre,
        produit_filtre=produit_filtre,
        partenaire_filtre=partenaire_filtre,
        partenaires=PARTENAIRES,
        archives=archives,
        tri=tri,
        q=q,
        du=du,
        au=au,
        dernieres=dernieres,
        manquantes=manquantes
    )


def proteger_csv(valeur):
    texte = "" if valeur is None else str(valeur)
    if texte[:1] in ("=", "+", "-", "@"):
        texte = "'" + texte
    return texte


@app.route("/equipe/dossiers/export.csv")
@login_required
def equipe_export_csv():
    if current_user.role != "admin":
        abort(404)

    statut_filtre = request.args.get("statut", "")
    profil_filtre = request.args.get("profil", "")
    produit_filtre = request.args.get("produit", "")
    partenaire_filtre = request.args.get("partenaire", "")
    archives = request.args.get("archives", "")
    q = request.args.get("q", "").strip()
    du = request.args.get("du", "")
    au = request.args.get("au", "")

    requete = Dossier.query

    for mot in q.split():
        motif = f"%{mot}%"
        requete = requete.filter(or_(
            Dossier.numero_dossier.like(motif),
            Dossier.reponses["nom"].as_string().collate("utf8mb4_general_ci").like(motif),
            Dossier.reponses["prenom"].as_string().collate("utf8mb4_general_ci").like(motif),
            Dossier.reponses["email"].as_string().collate("utf8mb4_general_ci").like(motif),
            Dossier.reponses["telephone"].as_string().collate("utf8mb4_general_ci").like(motif),
        ))

    if statut_filtre:
        requete = requete.filter(Dossier.statut == statut_filtre)
    if profil_filtre:
        requete = requete.filter(Dossier.reponses["profil"].as_string() == profil_filtre)
    if produit_filtre:
        requete = requete.filter(Dossier.reponses["besoin"].as_string() == produit_filtre)
    if partenaire_filtre in PARTENAIRES:
        requete = requete.filter(exists().where(and_(
            EtudePartenaire.dossier_id == Dossier.id,
            EtudePartenaire.partenaire == partenaire_filtre
        )))
    if archives == "1":
        requete = requete.filter(Dossier.archive.is_(True))
    else:
        requete = requete.filter(Dossier.archive.is_(False))
    if du:
        try:
            requete = requete.filter(Dossier.date_creation >= datetime.strptime(du, "%Y-%m-%d"))
        except ValueError:
            pass
    if au:
        try:
            requete = requete.filter(Dossier.date_creation < datetime.strptime(au, "%Y-%m-%d") + timedelta(days=1))
        except ValueError:
            pass

    dossiers = requete.order_by(Dossier.date_creation.desc()).all()
    libelles = dict(STATUTS)

    sortie = io.StringIO()
    ecrivain = csv.writer(sortie, delimiter=";")
    ecrivain.writerow(["Dossier", "Nom", "Prénom", "Téléphone", "E-mail", "Besoin", "Statut", "Date de création"])
    for d in dossiers:
        r = d.reponses or {}
        ecrivain.writerow([
            proteger_csv(d.numero_dossier),
            proteger_csv(r.get("nom", "")),
            proteger_csv(r.get("prenom", "")),
            proteger_csv(r.get("telephone", "")),
            proteger_csv(r.get("email", "")),
            proteger_csv(r.get("besoin", "")),
            proteger_csv(libelles.get(d.statut, d.statut)),
            heure_paris(d.date_creation, "%d/%m/%Y"),
        ])

    contenu = "\ufeff" + sortie.getvalue()
    nom_fichier = "dossiers_" + date.today().strftime("%Y-%m-%d") + ".csv"
    return Response(
        contenu,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=" + nom_fichier}
    )


@app.route("/equipe/dossiers/<int:dossier_id>")
@login_required
def equipe_fiche_dossier(dossier_id):
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)

    entrees = Historique.query.filter_by(dossier_id=dossier.id).order_by(Historique.date_creation.desc()).all()
    historique = []
    for e in entrees:
        auteur = Utilisateur.query.get(e.utilisateur_id) if e.utilisateur_id else None
        historique.append({
            "action": e.action,
            "date": e.date_creation,
            "auteur": f"{auteur.prenom} {auteur.nom}" if auteur else "Système"
        })

    lignes_notes = Note.query.filter_by(dossier_id=dossier.id).order_by(Note.date_creation.desc()).all()
    notes = []
    for n in lignes_notes:
        auteur = Utilisateur.query.get(n.utilisateur_id)
        notes.append({
            "contenu": n.contenu,
            "date": n.date_creation,
            "auteur": f"{auteur.prenom} {auteur.nom}" if auteur else "Inconnu"
        })

    lignes_demandes = DemandeDocuments.query.filter_by(dossier_id=dossier.id).order_by(DemandeDocuments.date_creation.desc()).all()
    demandes = []
    for dm in lignes_demandes:
        if dm.revoquee:
            etat = "Annulé"
        elif dm.date_expiration is None:
            etat = "Sans lien"
        elif dm.date_expiration < datetime.utcnow():
            etat = "Expiré"
        else:
            etat = "Actif"
        demandes.append({
            "id": dm.id,
            "date": dm.date_creation,
            "expiration": dm.date_expiration,
            "pieces": dm.pieces,
            "etat": etat
        })

    documents = Document.query.filter(Document.dossier_id == dossier.id, Document.statut != "supprime").order_by(Document.date_creation.desc()).all()
    supprimes = Document.query.filter(Document.dossier_id == dossier.id, Document.statut == "supprime").order_by(Document.date_creation.desc()).all()
    rappels = Rappel.query.filter_by(dossier_id=dossier.id).order_by(Rappel.fait.asc(), Rappel.date_rappel.asc()).all()
    etudes = EtudePartenaire.query.filter_by(dossier_id=dossier.id).order_by(EtudePartenaire.date_maj.desc()).all()

    reponses_dossier = dossier.reponses or {}
    email = (reponses_dossier.get("email") or "").strip()
    telephone = (reponses_dossier.get("telephone") or "").strip()

    criteres = []
    if email:
        criteres.append(Dossier.reponses["email"].as_string().collate("utf8mb4_general_ci") == email)
    if telephone:
        criteres.append(Dossier.reponses["telephone"].as_string() == telephone)

    memes_personnes = []
    if criteres:
        memes_personnes = Dossier.query.filter(
            Dossier.id != dossier.id,
            or_(*criteres)
        ).order_by(Dossier.date_creation.desc()).all()

    return render_template(
        "equipe_fiche_dossier.html",
        dossier=dossier,
        reponses=dossier.reponses or {},
        statuts=STATUTS,
        libelles=dict(STATUTS),
        historique=historique,
        notes=notes,
        demandes=demandes,
        pieces=PIECES,
        libelles_pieces={**dict(PIECES), **CATEGORIES_DEVIS},
        categories_devis=CATEGORIES_DEVIS,
        documents=documents,
        supprimes=supprimes,
        rappels=rappels,
        etudes=etudes,
        partenaires=PARTENAIRES,
        etats_etude=ETATS_ETUDE,
        libelles_etats=dict(ETATS_ETUDE),
        memes_personnes=memes_personnes
    )


def date_utc_texte(valeur):
    return valeur.strftime("%Y-%m-%d %H:%M:%S") + " UTC" if valeur else None


def donnees_dossier(dossier):
    return {
        "dossier": {
            "numero": dossier.numero_dossier,
            "statut": dossier.statut,
            "archive": dossier.archive,
            "date_creation": date_utc_texte(dossier.date_creation),
            "formulaire": dossier.reponses or {},
        },
        "historique": [
            {"date": date_utc_texte(h.date_creation), "action": h.action}
            for h in Historique.query.filter_by(dossier_id=dossier.id).order_by(Historique.date_creation.asc()).all()
        ],
        "notes": [
            {"date": date_utc_texte(n.date_creation), "contenu": n.contenu}
            for n in Note.query.filter_by(dossier_id=dossier.id).order_by(Note.date_creation.asc()).all()
        ],
        "rappels": [
            {"date_rappel": date_utc_texte(r.date_rappel), "contenu": r.contenu, "fait": r.fait}
            for r in Rappel.query.filter_by(dossier_id=dossier.id).order_by(Rappel.date_rappel.asc()).all()
        ],
        "demandes_de_documents": [
            {"date": date_utc_texte(dm.date_creation), "pieces": dm.pieces, "expiration": date_utc_texte(dm.date_expiration), "annulee": dm.revoquee}
            for dm in DemandeDocuments.query.filter_by(dossier_id=dossier.id).order_by(DemandeDocuments.date_creation.asc()).all()
        ],
        "documents_deposes": [
            {"date": date_utc_texte(doc.date_creation), "categorie": doc.categorie, "nom_original": doc.nom_original,
             "type": doc.type_reel, "taille_octets": doc.taille, "sha256": doc.sha256}
            for doc in Document.query.filter_by(dossier_id=dossier.id).order_by(Document.date_creation.asc()).all()
        ],
        "etudes_partenaires": [
            {"partenaire": e.partenaire, "etat": e.etat, "commentaire": e.commentaire, "mise_a_jour": date_utc_texte(e.date_maj)}
            for e in EtudePartenaire.query.filter_by(dossier_id=dossier.id).order_by(EtudePartenaire.date_creation.asc()).all()
        ],
        "remarque": "Les dates sont en heure UTC, sauf consentement_date (heure de Paris).",
    }


def pdf_dossier(dossier):
    historique = Historique.query.filter_by(dossier_id=dossier.id).order_by(Historique.date_creation.asc()).all()
    documents = Document.query.filter_by(dossier_id=dossier.id).order_by(Document.date_creation.asc()).all()
    html = render_template(
        "export_donnees_pdf.html",
        dossier=dossier,
        reponses=dossier.reponses or {},
        historique=historique,
        documents=documents,
        libelles_pieces={**dict(PIECES), **CATEGORIES_DEVIS},
        date_export=datetime.utcnow()
    )
    return HTML(string=html).write_pdf()


@app.route("/equipe/dossiers/<int:dossier_id>/export-complet")
@login_required
def equipe_export_complet(dossier_id):
    if current_user.role != "admin":
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    contenu_json = json.dumps(donnees_dossier(dossier), ensure_ascii=False, indent=2)
    contenu_pdf = pdf_dossier(dossier)

    db.session.add(Historique(
        dossier_id=dossier.id,
        utilisateur_id=current_user.id,
        action="Export des données du dossier (PDF et JSON)"
    ))
    db.session.commit()

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_fichier:
        zip_fichier.writestr(f"donnees_{dossier.numero_dossier}.pdf", contenu_pdf)
        zip_fichier.writestr(f"donnees_{dossier.numero_dossier}.json", contenu_json)

    return Response(
        archive.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=donnees_" + dossier.numero_dossier + ".zip"}
    )


@app.route("/equipe/dossiers/<int:dossier_id>/statut", methods=["POST"])
@login_required
def equipe_changer_statut(dossier_id):
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    nouveau_statut = request.form.get("statut")
    libelles = dict(STATUTS)

    if nouveau_statut in libelles and nouveau_statut != dossier.statut:
        ancien_statut = dossier.statut
        dossier.statut = nouveau_statut
        db.session.add(Historique(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            action=f"Statut changé de « {libelles.get(ancien_statut, ancien_statut)} » à « {libelles[nouveau_statut]} »"
        ))
        db.session.commit()
        flash(f"Statut enregistré avec succès : « {libelles[nouveau_statut]} ».", "succes")
    elif nouveau_statut == dossier.statut:
        flash("Ce statut est déjà celui du dossier : rien n'a été modifié.", "info")
    else:
        flash("Statut invalide : rien n'a été enregistré.", "erreur")

    return redirect(f"/equipe/dossiers/{dossier.id}")


@app.route("/equipe/dossiers/<int:dossier_id>/archivage", methods=["POST"])
@login_required
def equipe_archiver_dossier(dossier_id):
    if current_user.role != "admin":
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    action = request.form.get("action", "")

    if action == "archiver" and not dossier.archive:
        dossier.archive = True
        texte = "Dossier archivé"
    elif action == "desarchiver" and dossier.archive:
        dossier.archive = False
        texte = "Dossier désarchivé"
    else:
        return redirect(f"/equipe/dossiers/{dossier.id}")

    db.session.add(Historique(
        dossier_id=dossier.id,
        utilisateur_id=current_user.id,
        action=texte
    ))
    db.session.commit()

    return redirect(f"/equipe/dossiers/{dossier.id}")


@app.route("/equipe/dossiers/<int:dossier_id>/notes", methods=["POST"])
@login_required
def equipe_ajouter_note(dossier_id):
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    contenu = request.form.get("contenu", "").strip()

    if contenu:
        db.session.add(Note(dossier_id=dossier.id, utilisateur_id=current_user.id, contenu=contenu))
        db.session.add(Historique(dossier_id=dossier.id, utilisateur_id=current_user.id, action="Note interne ajoutée"))
        db.session.commit()

    return redirect(f"/equipe/dossiers/{dossier.id}")


@app.route("/equipe/dossiers/<int:dossier_id>/rappels", methods=["POST"])
@login_required
def equipe_ajouter_rappel(dossier_id):
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    contenu = request.form.get("contenu", "").strip()
    date_texte = request.form.get("date_rappel", "")

    if contenu and date_texte:
        try:
            date_locale = datetime.strptime(date_texte, "%Y-%m-%dT%H:%M")
        except ValueError:
            return redirect(f"/equipe/dossiers/{dossier.id}")

        date_utc = date_locale.replace(tzinfo=ZoneInfo("Europe/Paris")).astimezone(timezone.utc).replace(tzinfo=None)

        db.session.add(Rappel(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            date_rappel=date_utc,
            contenu=contenu[:255]
        ))
        db.session.add(Historique(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            action="Rappel ajouté : " + contenu[:100]
        ))
        db.session.commit()

    return redirect(f"/equipe/dossiers/{dossier.id}")


@app.route("/equipe/dossiers/<int:dossier_id>/rappels/<int:rappel_id>/fait", methods=["POST"])
@login_required
def equipe_rappel_fait(dossier_id, rappel_id):
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    rappel = Rappel.query.get_or_404(rappel_id)

    if rappel.dossier_id == dossier.id and not rappel.fait:
        rappel.fait = True
        rappel.date_fait = datetime.utcnow()
        db.session.add(Historique(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            action="Rappel terminé : " + rappel.contenu[:100]
        ))
        db.session.commit()

    return redirect(f"/equipe/dossiers/{dossier.id}")


@app.route("/equipe/dossiers/<int:dossier_id>/partenaires", methods=["POST"])
@login_required
def equipe_ajouter_partenaire(dossier_id):
    if current_user.role not in ROLES_EQUIPE:
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    partenaire = request.form.get("partenaire", "")
    etat = request.form.get("etat", "")
    commentaire = request.form.get("commentaire", "").strip()
    libelles_etats = dict(ETATS_ETUDE)

    if partenaire in PARTENAIRES and etat in libelles_etats:
        db.session.add(EtudePartenaire(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            partenaire=partenaire,
            etat=etat,
            commentaire=commentaire[:255]
        ))
        db.session.add(Historique(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            action=f"Partenaire : {partenaire} · {libelles_etats[etat]}"
        ))
        db.session.commit()

    return redirect(f"/equipe/dossiers/{dossier.id}")


@app.route("/equipe/dossiers/<int:dossier_id>/demande-documents", methods=["POST"])
@login_required
def equipe_demander_documents(dossier_id):
    if current_user.role != "admin":
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    libelles = dict(PIECES)
    choisies = [p for p in request.form.getlist("pieces") if p in libelles]

    if choisies:
        token = secrets.token_urlsafe(32)
        expiration = datetime.utcnow() + timedelta(hours=DUREE_LIEN_HEURES)

        db.session.add(DemandeDocuments(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            pieces=choisies,
            token=token,
            date_expiration=expiration
        ))
        noms_pieces = [libelles[p] for p in choisies]
        db.session.add(Historique(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            action="Documents demandés : " + ", ".join(noms_pieces) + f" (lien valable {DUREE_LIEN_HEURES} h)"
        ))
        db.session.commit()

        email_client = (dossier.reponses or {}).get("email")
        lien = f"{request.host_url}depot/{token}"
        if email_client:
            try:
                envoyer_demande_documents(email_client, lien, noms_pieces, dossier.numero_dossier)
            except Exception as erreur:
                print(f"[ERREUR E-MAIL] {erreur}")

    return redirect(f"/equipe/dossiers/{dossier.id}")


@app.route("/equipe/dossiers/<int:dossier_id>/demande-documents/<int:demande_id>/revoquer", methods=["POST"])
@login_required
def equipe_revoquer_demande(dossier_id, demande_id):
    if current_user.role != "admin":
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    demande = DemandeDocuments.query.get_or_404(demande_id)

    if demande.dossier_id == dossier.id and not demande.revoquee:
        demande.revoquee = True
        db.session.add(Historique(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            action="Lien de dépôt annulé"
        ))
        db.session.commit()

    return redirect(f"/equipe/dossiers/{dossier.id}")


def verifier_lien(token):
    demande = DemandeDocuments.query.filter_by(token=token).first()
    if (demande is not None
            and not demande.revoquee
            and demande.date_expiration is not None
            and demande.date_expiration > datetime.utcnow()):
        return demande
    return None


@app.route("/depot/<token>", methods=["GET", "POST"])
def depot_page(token):
    demande = verifier_lien(token)
    if demande is None:
        return render_template("depot_invalide.html"), 404

    dossier = Dossier.query.get(demande.dossier_id)
    libelles = dict(PIECES)
    pieces = [(p, libelles.get(p, p)) for p in demande.pieces]

    if request.method == "POST":
        acceptes = []
        refuses = []
        envoyes = []

        for valeur, libelle in pieces:
            fichier = request.files.get(f"fichier_{valeur}")
            if fichier is None or fichier.filename == "":
                continue

            contenu = fichier.read()

            if len(contenu) == 0:
                refuses.append((libelle, "Le fichier est vide."))
                continue
            if len(contenu) > TAILLE_MAX_FICHIER:
                refuses.append((libelle, "Le fichier dépasse 10 Mo."))
                continue

            type_detecte = filetype.guess(contenu)
            if type_detecte is None or type_detecte.mime not in TYPES_AUTORISES:
                refuses.append((libelle, "Format non accepté : seuls les PDF, JPG et PNG sont autorisés."))
                continue

            extension = TYPES_AUTORISES[type_detecte.mime]
            nom_stocke = f"{uuid.uuid4().hex}.{extension}"
            empreinte = hashlib.sha256(contenu).hexdigest()

            try:
                enregistrer_fichier(contenu, nom_stocke, type_detecte.mime)
            except StockageErreur:
                refuses.append((libelle, "Le service d'envoi est momentanément indisponible. Merci de réessayer dans quelques minutes."))
                continue

            envoyes.append(nom_stocke)
            db.session.add(Document(
                dossier_id=dossier.id,
                demande_id=demande.id,
                categorie=valeur,
                nom_original=fichier.filename[:255],
                nom_stocke=nom_stocke,
                type_reel=type_detecte.mime,
                taille=len(contenu),
                sha256=empreinte
            ))
            acceptes.append(libelle)

        if acceptes:
            numero = dossier.numero_dossier
            try:
                db.session.add(Historique(
                    dossier_id=dossier.id,
                    action="Documents déposés par le client : " + ", ".join(acceptes)
                ))
                db.session.commit()
            except Exception as erreur:
                db.session.rollback()
                print(f"[ERREUR BASE] {erreur}")
                for nom in envoyes:
                    try:
                        supprimer_fichier(nom)
                    except StockageErreur:
                        print(f"[ATTENTION] fichier orphelin à supprimer : {nom}")
                for libelle in acceptes:
                    refuses.append((libelle, "Une erreur est survenue. Merci de réessayer dans quelques minutes."))
                acceptes = []
            else:
                try:
                    notifier_equipe_depot(numero, acceptes)
                except Exception as erreur:
                    print(f"[ERREUR E-MAIL] {erreur}")

        if not acceptes and not refuses:
            refuses.append(("", "Aucun fichier n'a été sélectionné."))

        return render_template("depot_resultat.html", acceptes=acceptes, refuses=refuses, token=token)

    return render_template(
        "depot.html",
        token=token,
        numero_dossier=dossier.numero_dossier,
        pieces=pieces,
        expiration=demande.date_expiration
    )


@app.errorhandler(413)
def envoi_trop_gros(erreur):
    return render_template(
        "depot_resultat.html",
        acceptes=[],
        refuses=[("", "L'envoi est trop volumineux (10 Mo maximum par fichier).")],
        token=None
    ), 413


@app.route("/equipe/documents/<int:document_id>/telecharger")
@login_required
def equipe_telecharger_document(document_id):
    if current_user.role != "admin":
        abort(404)
    document = Document.query.get_or_404(document_id)

    if document.statut == "supprime":
        abort(404)

    try:
        if existe_dans_bucket(document.nom_stocke):
            adresse = adresse_temporaire(document.nom_stocke, 60, document.nom_original, document.type_reel)
            contenu = None
        else:
            adresse = None
            contenu = lire_fichier(document.nom_stocke, document.sha256)
    except StockageErreur:
        return Response(
            "Le document est momentanément indisponible. Merci de réessayer dans quelques minutes.",
            status=503,
            content_type="text/plain; charset=utf-8"
        )

    db.session.add(Historique(
        dossier_id=document.dossier_id,
        utilisateur_id=current_user.id,
        action="Document ouvert : " + document.nom_original
    ))
    db.session.commit()

    if adresse:
        return redirect(adresse)

    return Response(
        contenu,
        mimetype=document.type_reel,
        headers={"Content-Disposition": "inline; filename=" + document.nom_stocke}
    )


@app.route("/equipe/dossiers/<int:dossier_id>/devis-assureur", methods=["POST"])
@login_required
def equipe_ajouter_devis_assureur(dossier_id):
    if current_user.role != "admin":
        abort(404)

    dossier = Dossier.query.get_or_404(dossier_id)
    retour = f"/equipe/dossiers/{dossier.id}"
    categorie = request.form.get("categorie", "")
    fichier = request.files.get("fichier")

    if categorie not in CATEGORIES_DEVIS:
        flash("Assureur invalide : rien n'a été enregistré.", "erreur")
        return redirect(retour)
    if fichier is None or fichier.filename == "":
        flash("Aucun fichier sélectionné.", "erreur")
        return redirect(retour)

    contenu = fichier.read()
    if len(contenu) == 0:
        flash("Le fichier est vide.", "erreur")
        return redirect(retour)
    if len(contenu) > TAILLE_MAX_FICHIER:
        flash("Le fichier dépasse 10 Mo.", "erreur")
        return redirect(retour)

    type_detecte = filetype.guess(contenu)
    if type_detecte is None or type_detecte.mime not in TYPES_AUTORISES:
        flash("Format non accepté : seuls les PDF, JPG et PNG sont autorisés.", "erreur")
        return redirect(retour)

    nom_stocke = f"{uuid.uuid4().hex}.{TYPES_AUTORISES[type_detecte.mime]}"
    empreinte = hashlib.sha256(contenu).hexdigest()

    try:
        enregistrer_fichier(contenu, nom_stocke, type_detecte.mime)
    except StockageErreur:
        flash("Le stockage est momentanément indisponible. Merci de réessayer.", "erreur")
        return redirect(retour)

    try:
        db.session.add(Document(
            dossier_id=dossier.id,
            categorie=categorie,
            nom_original=fichier.filename[:255],
            nom_stocke=nom_stocke,
            type_reel=type_detecte.mime,
            taille=len(contenu),
            sha256=empreinte,
            source="equipe"
        ))
        db.session.add(Historique(
            dossier_id=dossier.id,
            utilisateur_id=current_user.id,
            action=f"{CATEGORIES_DEVIS[categorie]} ajouté : {fichier.filename[:100]}"
        ))
        db.session.commit()
    except Exception as erreur:
        db.session.rollback()
        print(f"[ERREUR BASE] {erreur}")
        try:
            supprimer_fichier(nom_stocke)
        except StockageErreur:
            print(f"[ATTENTION] fichier orphelin à supprimer : {nom_stocke}")
        flash("Une erreur est survenue : le devis n'a pas été enregistré.", "erreur")
        return redirect(retour)

    flash(f"{CATEGORIES_DEVIS[categorie]} enregistré avec succès.", "succes")
    return redirect(retour)


@app.route("/equipe/documents/<int:document_id>/supprimer", methods=["POST"])
@login_required
def equipe_supprimer_document(document_id):
    if current_user.role != "admin":
        abort(404)

    document = Document.query.get_or_404(document_id)

    if document.statut != "supprime":
        document.statut = "supprime"
        db.session.add(Historique(
            dossier_id=document.dossier_id,
            utilisateur_id=current_user.id,
            action="Document supprimé (corbeille) : " + document.nom_original
        ))
        db.session.commit()

    return redirect(f"/equipe/dossiers/{document.dossier_id}")


@app.route("/equipe/documents/<int:document_id>/restaurer", methods=["POST"])
@login_required
def equipe_restaurer_document(document_id):
    if current_user.role != "admin":
        abort(404)

    document = Document.query.get_or_404(document_id)

    if document.statut == "supprime":
        document.statut = "recu"
        db.session.add(Historique(
            dossier_id=document.dossier_id,
            utilisateur_id=current_user.id,
            action="Document restauré : " + document.nom_original
        ))
        db.session.commit()

    return redirect(f"/equipe/dossiers/{document.dossier_id}")


@app.route("/equipe/documents/<int:document_id>/supprimer-definitivement", methods=["POST"])
@login_required
def equipe_supprimer_definitivement(document_id):
    if current_user.role != "admin":
        abort(404)

    document = Document.query.get_or_404(document_id)
    if document.statut != "supprime":
        abort(404)

    try:
        supprimer_fichier(document.nom_stocke)
    except StockageErreur:
        return Response(
            "Suppression impossible pour le moment. Merci de réessayer plus tard.",
            status=503,
            content_type="text/plain; charset=utf-8"
        )

    dossier_id = document.dossier_id
    db.session.add(Historique(
        dossier_id=dossier_id,
        utilisateur_id=current_user.id,
        action="Document supprimé définitivement : " + document.nom_original
    ))
    db.session.delete(document)
    db.session.commit()

    return redirect(f"/equipe/dossiers/{dossier_id}")


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)