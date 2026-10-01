from app import app
from models import db, Produit

produits = [
    {
        "nom": "Mutuelle santé particuliers",
        "description": "Une complémentaire santé adaptée à votre situation, pour vous et vos proches.",
        "presentation": "Chaque famille a des besoins de santé différents. Notre mutuelle santé particuliers s'adapte à votre situation, que vous soyez seul, en couple ou avec des enfants, pour vous garantir un accès aux soins sans mauvaise surprise financière.",
        "categorie": "Santé",
        "garanties": [
            "Remboursement des consultations, hospitalisations et médicaments",
            "Options dentaire et optique modulables",
            "Formules adaptées aux familles",
            "Tiers payant chez la plupart des professionnels de santé"
        ],
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"}
            ]
        }
    },
    {
        "nom": "Mutuelle santé seniors",
        "description": "Une couverture santé pensée pour les besoins spécifiques des seniors.",
        "presentation": "Avec l'âge, les besoins de santé évoluent, et les remboursements de la Sécurité sociale ne suffisent souvent plus à couvrir certains soins. Notre mutuelle santé seniors a été pensée pour vous accompagner sans limite d'âge, avec des garanties renforcées sur les postes de dépense les plus fréquents après 60 ans.",
        "categorie": "Santé",
        "garanties": [
            "Remboursement renforcé des soins dentaires et optiques",
            "Prise en charge des dépassements d'honoraires",
            "Aucune limite d'âge à l'adhésion",
            "Assistance et téléconsultation incluses"
        ],
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"}
            ]
        }
    },
    {
        "nom": "Mutuelle santé TNS",
        "description": "Complémentaire santé pensée pour les indépendants et chefs d'entreprise.",
        "presentation": "En tant qu'indépendant ou chef d'entreprise, vous ne bénéficiez pas toujours des mêmes protections qu'un salarié. Notre mutuelle santé TNS vous permet de choisir un niveau de couverture adapté à votre activité et à votre budget, avec la possibilité de déduire vos cotisations selon votre statut.",
        "categorie": "Santé TNS",
        "garanties": [
            "Cotisations potentiellement déductibles du revenu professionnel",
            "Formules ajustables selon votre activité",
            "Couverture hospitalisation, dentaire et optique",
            "Accompagnement dédié aux indépendants"
        ],
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"}
            ]
        }
    },
    {
        "nom": "Prévoyance TNS",
        "description": "Maintien de revenu en cas d'arrêt de travail, invalidité ou décès, pour les indépendants.",
        "presentation": "Un arrêt de travail ou un imprévu peut mettre en péril les revenus d'un indépendant, qui ne bénéficie pas des mêmes filets de sécurité qu'un salarié. Notre contrat de prévoyance TNS vous garantit un maintien de revenu, pour vous et votre famille, en cas de coup dur.",
        "categorie": "Prévoyance TNS",
        "garanties": [
            "Indemnités journalières en cas d'arrêt de travail",
            "Rente en cas d'invalidité",
            "Capital versé aux proches en cas de décès",
            "Niveau de garantie ajustable selon vos revenus"
        ],
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"},
                {"nom": "date_naissance", "label": "Date de naissance", "type": "date"}
            ]
        }
    },
    {
        "nom": "Assurance emprunteur",
        "description": "Sécurisez votre projet immobilier ou professionnel avec une couverture adaptée.",
        "presentation": "Un crédit immobilier ou professionnel engage sur plusieurs années. Notre assurance emprunteur vous protège, vous et vos proches, en prenant le relais du remboursement en cas d'événement grave, pour que votre projet reste sécurisé quoi qu'il arrive.",
        "categorie": "Emprunteur",
        "garanties": [
            "Prise en charge du remboursement en cas de décès ou invalidité",
            "Couverture adaptée aux crédits immobiliers et professionnels",
            "Possibilité de délégation d'assurance",
            "Étude personnalisée selon votre profil"
        ],
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"}
            ]
        }
    },
    {
        "nom": "Plan Épargne Retraite",
        "description": "Constituez votre épargne retraite avec un cadre fiscal avantageux.",
        "presentation": "Préparer sa retraite demande d'anticiper tôt. Le Plan Épargne Retraite vous permet de constituer une épargne à votre rythme, tout en bénéficiant d'avantages fiscaux, pour aborder cette nouvelle étape de vie plus sereinement.",
        "categorie": "Retraite",
        "garanties": [
            "Versements libres ou programmés",
            "Avantage fiscal sur les sommes versées",
            "Sortie possible en capital ou en rente",
            "Adapté aux salariés comme aux indépendants"
        ],
        "formulaire_schema": {
            "champs": [
                {"nom": "nom", "label": "Nom", "type": "text"},
                {"nom": "prenom", "label": "Prénom", "type": "text"},
                {"nom": "email", "label": "E-mail", "type": "email"}
            ]
        }
    },
]

with app.app_context():
    for p in produits:
        existe_deja = Produit.query.filter_by(nom=p["nom"]).first()
        if existe_deja:
            existe_deja.description = p["description"]
            existe_deja.presentation = p["presentation"]
            existe_deja.categorie = p["categorie"]
            existe_deja.garanties = p["garanties"]
            existe_deja.formulaire_schema = p["formulaire_schema"]
        else:
            nouveau_produit = Produit(**p)
            db.session.add(nouveau_produit)
    db.session.commit()
    print("Produits insérés/mis à jour avec succès !")