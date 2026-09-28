from datetime import date, datetime

def calculer_age(date_naissance_texte):
    date_naissance = datetime.strptime(date_naissance_texte, "%Y-%m-%d").date()
    aujourd_hui = date.today()
    age = aujourd_hui.year - date_naissance.year
    if (aujourd_hui.month, aujourd_hui.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age


def calculer_devis_interne(produit, reponses):
    nom_produit = produit.nom

    if nom_produit == "Multirisque professionnelle":
        surface = float(reponses.get("surface_locaux", 0))
        valeur_materiel = float(reponses.get("valeur_materiel", 0))
        prix = 15 + (surface * 0.05) + (valeur_materiel * 0.002)

    elif nom_produit == "Responsabilité civile pro":
        chiffre_affaires = float(reponses.get("chiffre_affaires", 0))
        prix = 10 + (chiffre_affaires * 0.0015)

    elif nom_produit == "Mutuelle TNS":
        age = calculer_age(reponses.get("date_naissance"))
        prix = 20 + (age * 0.5)

        modificateurs = {
            "Célibataire": 0,
            "Marié(e) / Pacsé(e)": 12,
            "Divorcé(e)": 0,
            "Veuf(ve)": 0
        }
        situation = reponses.get("situation_familiale")
        prix += modificateurs.get(situation, 0)

    elif nom_produit == "Prévoyance indépendant":
        revenu = float(reponses.get("revenu_annuel", 0))
        prix = 15 + (revenu * 0.001)

    elif nom_produit == "Plan Épargne Retraite":
        versement = float(reponses.get("versement_mensuel_souhaite", 0))
        prix = versement * 0.02

    elif nom_produit == "Retraite complémentaire":
        age = calculer_age(reponses.get("date_naissance"))
        prix = 8 + (age * 0.35)

        modificateurs = {
            "Salarié": 0,
            "Indépendant": 8,
            "Profession libérale": 8,
            "Fonctionnaire": -3
        }
        statut = reponses.get("statut_professionnel")
        prix += modificateurs.get(statut, 0)

    else:
        prix = 25

    return round(prix, 2)


def obtenir_devis(produit, reponses):
    prix = calculer_devis_interne(produit, reponses)
    return {
        "prix": prix,
        "provider": "interne"
    }