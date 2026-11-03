"""Prépare la base de DÉMONSTRATION en ligne : tables, catalogue, données fictives.

Usage (depuis le dossier backend) :
    DEMO_DATABASE_URL="mysql://...?ssl-mode=REQUIRED" python preparer_demo.py

Garde-fous :
- n'utilise jamais DATABASE_URL ni le fichier .env : seulement DEMO_DATABASE_URL ;
- refuse les adresses locales (localhost, 127.0.0.1, conteneur Docker « mysql ») ;
- ne supprime rien et ne modifie aucun dossier existant : n'ajoute que ce qui manque.
Toutes les personnes et coordonnées créées sont fictives (domaine example.com).
"""
import os
import secrets
import sys
from datetime import datetime, timedelta

from sqlalchemy.engine import make_url

HOTES_INTERDITS = {"localhost", "127.0.0.1", "::1", "mysql", "host.docker.internal", ""}

url_demo = os.environ.get("DEMO_DATABASE_URL", "").strip()
if not url_demo:
    sys.exit("DEMO_DATABASE_URL n'est pas définie : rien n'a été fait.")
hote = (make_url(url_demo.replace("mysql://", "mysql+pymysql://", 1)).host or "").lower()
if hote in HOTES_INTERDITS:
    sys.exit(f"Adresse refusée ({hote or 'vide'}) : ce script ne s'utilise que sur la base de démonstration en ligne.")

# Impose la base de démo avant l'import de l'application (load_dotenv n'écrase pas une variable déjà définie).
os.environ["DATABASE_URL"] = url_demo
os.environ["CREER_TABLES_AU_DEMARRAGE"] = "0"

import bcrypt  # noqa: E402
from app import app  # noqa: E402
from models import db, Utilisateur, Dossier, Historique, Note, Rappel, EtudePartenaire  # noqa: E402

EMAIL_DEMO = "demo.equipe@example.com"

DOSSIERS_FICTIFS = [
    ("DEMO-0001", "nouveau", "Madame", "Durand", "Claire", "34", "Mariée", "2", "Particulier", "Mutuelle santé", "Souhaite comparer avec sa mutuelle actuelle."),
    ("DEMO-0002", "a_contacter", "Monsieur", "Moreau", "Julien", "45", "Pacsé(e)", "1", "Professionnel", "Prévoyance TNS", "Artisan, création d'entreprise récente."),
    ("DEMO-0003", "en_attente_de_pieces", "Madame", "Lefèvre", "Sophie", "29", "Célibataire", "0", "Particulier", "Assurance emprunteur", "Projet d'achat immobilier."),
    ("DEMO-0004", "devis_en_cours", "Monsieur", "Garnier", "Thomas", "52", "Marié(e)", "3", "Professionnel", "Santé TNS", "Rappeler en fin de journée."),
    ("DEMO-0005", "proposition_envoyee", "Madame", "Bonnet", "Élise", "67", "Veuf(ve)", "0", "Particulier", "Mutuelle santé seniors", ""),
    ("DEMO-0006", "client", "Monsieur", "Fontaine", "Hugo", "38", "Union libre", "2", "Particulier", "Plan Épargne Retraite", "Dossier finalisé (exemple)."),
]


def creer_compte_demo():
    compte = Utilisateur.query.filter_by(email=EMAIL_DEMO).first()
    if compte:
        print(f"Compte de démonstration déjà présent : {EMAIL_DEMO} (mot de passe inchangé).")
        return compte
    mot_de_passe = os.environ.get("DEMO_MOT_DE_PASSE") or secrets.token_urlsafe(12)
    compte = Utilisateur(
        nom="Démo", prenom="Équipe", email=EMAIL_DEMO, role="admin",
        mot_de_passe=bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
    )
    db.session.add(compte)
    db.session.commit()
    print(f"Compte de démonstration créé : {EMAIL_DEMO}")
    if not os.environ.get("DEMO_MOT_DE_PASSE"):
        print(f"Mot de passe généré (affiché une seule fois, à conserver hors de Git) : {mot_de_passe}")
    return compte


def creer_dossiers(compte):
    maintenant = datetime.utcnow()
    ajoutes = 0
    for i, (numero, statut, civ, nom, prenom, age, situation, enfants, profil, besoin, commentaire) in enumerate(DOSSIERS_FICTIFS):
        if Dossier.query.filter_by(numero_dossier=numero).first():
            continue
        cree_le = maintenant - timedelta(days=12 - 2 * i)
        dossier = Dossier(
            numero_dossier=numero, statut=statut, source="demo", date_creation=cree_le,
            reponses={
                "civilite": civ, "nom": nom, "prenom": prenom,
                "telephone": f"06 00 00 00 0{i + 1}",
                "email": f"{prenom.lower().replace('é', 'e')}.{nom.lower().replace('è', 'e')}@example.com",
                "age": age, "situation_matrimoniale": situation, "nombre_enfants": enfants,
                "famille_nombreuse": "Oui" if int(enfants) >= 3 else "Non",
                "profil": profil, "besoin": besoin,
                "moyen_contact_prefere": "Téléphone", "creneau_souhaite": "10h30 - 11h30",
                "commentaire": commentaire,
                "consentement_rgpd": True,
                "consentement_date": cree_le.strftime("%Y-%m-%d %H:%M:%S"),
                "consentement_texte": "Données fictives de démonstration.",
                "donnees_fictives": True,
            },
        )
        db.session.add(dossier)
        db.session.flush()
        db.session.add(Historique(dossier_id=dossier.id, action="Dossier fictif créé pour la démonstration", date_creation=cree_le))
        if statut != "nouveau":
            db.session.add(Note(dossier_id=dossier.id, utilisateur_id=compte.id, contenu="Note de démonstration : premier échange téléphonique."))
        if statut in ("a_contacter", "devis_en_cours"):
            db.session.add(Rappel(dossier_id=dossier.id, utilisateur_id=compte.id,
                                  date_rappel=maintenant + timedelta(days=1), contenu="Rappel fictif : recontacter le client."))
        if statut in ("devis_en_cours", "proposition_envoyee", "client"):
            db.session.add(EtudePartenaire(dossier_id=dossier.id, utilisateur_id=compte.id, partenaire="SPVIE",
                                           etat="reponse_recue", commentaire="Étude fictive."))
        ajoutes += 1
    db.session.commit()
    print(f"Dossiers fictifs ajoutés : {ajoutes} (déjà présents : {len(DOSSIERS_FICTIFS) - ajoutes}).")


if __name__ == "__main__":
    print(f"Base ciblée : {hote}")
    with app.app_context():
        db.create_all()
        print("Tables vérifiées / créées.")
    import seed  # noqa: E402,F401  (met à jour le catalogue des produits dans la base ciblée)
    print("Catalogue des produits à jour.")
    with app.app_context():
        creer_dossiers(creer_compte_demo())
    print("Préparation terminée.")
