from flask import Flask, render_template, request, redirect, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import os
import bcrypt
import base64
from datetime import date, datetime
from weasyprint import HTML
from models import db, Produit, Dossier, Devis, Contrat, Signature, Utilisateur
from moteur_devis import obtenir_devis
from mailer import configurer_mail, envoyer_documents, envoyer_accuse_reception, notifier_equipe_nouvelle_demande

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-moi-plus-tard')
AFFICHER_FONCTIONNALITES_MASQUEES = os.getenv('AFFICHER_FONCTIONNALITES_MASQUEES', 'False') == 'True'
db.init_app(app)
configurer_mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "compte"

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
    produits = Produit.query.all()
    return render_template(
        "liste_produits.html",
        produits=produits,
        titre="Particuliers",
        sous_titre="Nos solutions pour vous et vos proches.",
        vers_devis=False
    )

@app.route("/professionnels")
def page_professionnels():
    produits = Produit.query.all()
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
    return render_template("espace_client.html")


@app.route("/deconnexion")
def deconnexion():
    logout_user()
    return redirect("/")


@app.route("/contact", methods=["POST"])
def contact():
    reponses = {
        "civilite": request.form.get("civilite"),
        "nom": request.form.get("nom"),
        "prenom": request.form.get("prenom"),
        "telephone": request.form.get("telephone"),
        "email": request.form.get("email"),
        "code_postal": request.form.get("code_postal"),
        "ville": request.form.get("ville"),
        "profil": request.form.get("profil"),
        "besoin": request.form.get("besoin"),
        "moyen_contact_prefere": request.form.get("moyen_contact_prefere"),
        "creneau_souhaite": request.form.get("creneau_souhaite"),
        "commentaire": request.form.get("commentaire"),
    }

    champs_obligatoires = ["civilite", "nom", "prenom", "telephone", "email", "code_postal", "ville", "profil", "besoin"]
    champ_manquant = False
    for champ in champs_obligatoires:
        if not reponses[champ]:
            champ_manquant = True

    if champ_manquant:
        produits = Produit.query.all()
        return render_template("accueil.html", produits=produits, numero_dossier=None, erreur_formulaire="Merci de remplir tous les champs obligatoires avant d'envoyer votre demande.")

    nouveau_dossier = Dossier(
        statut="nouveau",
        source="interne",
        reponses=reponses
    )
    db.session.add(nouveau_dossier)
    db.session.commit()

    nouveau_dossier.numero_dossier = f"PRV-{date.today().year}-{nouveau_dossier.id:06d}"
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

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)