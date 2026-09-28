from app import app
from models import db, Produit

produits = [
    {
        "nom": "Multirisque professionnelle",
        "description": "Locaux, matériel, marchandises protégez les actifs de votre activité.",
        "categorie": "Assurance de biens",
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "activite", "label": "Activité professionnelle", "type": "text"},
                {"nom": "surface_locaux", "label": "Surface des locaux (m²)", "type": "number"},
                {"nom": "valeur_materiel", "label": "Valeur du matériel (€)", "type": "number"}
            ]
        }
    },
    {
        "nom": "Responsabilité civile pro",
        "description": "Couverture des dommages causés à des tiers dans le cadre de votre activité.",
        "categorie": "RC Pro",
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "activite", "label": "Activité professionnelle", "type": "text"},
                {"nom": "chiffre_affaires", "label": "Chiffre d'affaires annuel (€)", "type": "number"},
                {"nom": "forme_juridique", "label": "Forme juridique", "type": "select",
                 "options": ["Auto-entrepreneur", "SASU", "EURL", "SARL"]}
            ]
        }
    },
    {
        "nom": "Mutuelle TNS",
        "description": "Complémentaire santé pensée pour les indépendants et chefs d'entreprise.",
        "categorie": "Mutuelle santé",
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"},
                {"nom": "situation_familiale", "label": "Situation familiale", "type": "select",
                 "options": ["Célibataire", "Marié(e) / Pacsé(e)", "Divorcé(e)", "Veuf(ve)"]}
            ]
        }
    },
    {
        "nom": "Prévoyance indépendant",
        "description": "Maintien de revenu en cas d'arrêt de travail, invalidité ou décès.",
        "categorie": "Prévoyance",
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"},
                {"nom": "revenu_annuel", "label": "Revenu annuel (€)", "type": "number"}
            ]
        }
    },
    {
        "nom": "Plan Épargne Retraite",
        "description": "Constituez votre épargne retraite avec un cadre fiscal avantageux.",
        "categorie": "PER",
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"},
                {"nom": "versement_mensuel_souhaite", "label": "Versement mensuel souhaité (€)", "type": "number"}
            ]
        }
    },
    {
        "nom": "Retraite complémentaire",
        "description": "Complétez vos droits à la retraite selon votre statut professionnel.",
        "categorie": "Retraite complémentaire",
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"},
                {"nom": "statut_professionnel", "label": "Statut professionnel", "type": "select",
                 "options": ["Salarié", "Indépendant", "Profession libérale", "Fonctionnaire"]}
            ]
        }
    },
]

with app.app_context():
    for p in produits:
        existe_deja = Produit.query.filter_by(nom=p["nom"]).first()
        if existe_deja:
            existe_deja.formulaire_schema = p["formulaire_schema"]
        else:
            nouveau_produit = Produit(**p)
            db.session.add(nouveau_produit)
    db.session.commit()
    print("Produits insérés/mis à jour avec succès !")