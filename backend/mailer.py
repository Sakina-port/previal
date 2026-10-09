import os
from flask_mail import Mail, Message


mail = Mail()

def configurer_mail(app):
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    mail.init_app(app)

def envoyer_accuse_reception(destinataire, numero_dossier):
    if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD'):
        print(f"[E-MAIL NON ENVOYÉ] Accusé de réception. Destinataire prévu : {destinataire}")
        return False

    msg = Message(
        subject=f"PREVIAL - Nous avons bien reçu votre demande ({numero_dossier})",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[destinataire],
        body=f"Bonjour,\n\nNous avons bien reçu votre demande (dossier {numero_dossier}).\nUn conseiller Prévial va vous recontacter prochainement.\n\nCordialement,\nL'équipe Prévial"
    )
    mail.send(msg)
    return True


def notifier_equipe_nouvelle_demande(numero_dossier, besoin, nom, prenom, commentaire):
    if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD'):
        print(f"[E-MAIL NON ENVOYÉ] Notification équipe pour {numero_dossier}")
        return False
    texte_commentaire = commentaire if commentaire else "Aucun commentaire laissé"

    msg = Message(
        subject=f"PREVIAL - Nouvelle demande {numero_dossier}",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=["sakinaawa123@gmail.com"],
        body=f"Nouvelle demande de contact.\n\nDossier : {numero_dossier}\nDe : {prenom} {nom}\nBesoin : {besoin}\nCommentaire : {texte_commentaire}\n\nConsultez l'espace privé pour le détail complet."
    )
    mail.send(msg)
    return True

def envoyer_documents(destinataire, produit_nom, dossier_id, chemin_devis, chemin_contrat):
    if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD'):
        print(f"[E-MAIL NON ENVOYÉ] Configuration manquante dans .env. Destinataire prévu : {destinataire}")
        return False

    msg = Message(
        subject=f"PREVIAL Votre contrat {produit_nom}",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[destinataire],
        body=f"Bonjour,\n\nVeuillez trouver ci-joint votre devis et votre contrat pour {produit_nom} (dossier n°{dossier_id}).\n\nCordialement,\nL'équipe Prévial"
    )

    with open(chemin_devis, 'rb') as f:
        msg.attach("devis.pdf", "application/pdf", f.read())
    with open(chemin_contrat, 'rb') as f:
        msg.attach("contrat.pdf", "application/pdf", f.read())

    mail.send(msg)
    return True


def envoyer_demande_documents(destinataire, lien, pieces, numero_dossier):
    if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD'):
        print(f"[E-MAIL NON ENVOYÉ] Demande de documents pour {destinataire}. Lien : {lien}")
        return False

    liste_pieces = "\n".join(f"- {p}" for p in pieces)

    msg = Message(
        subject=f"PREVIAL - Documents à nous transmettre ({numero_dossier})",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[destinataire],
        body=f"Bonjour,\n\nPour avancer sur votre dossier {numero_dossier}, merci de nous transmettre les documents suivants :\n{liste_pieces}\n\nVous pouvez les déposer de façon sécurisée avec ce lien, valable 48 heures :\n{lien}\n\nMerci de ne nous envoyer aucun document médical.\n\nCordialement,\nL'équipe PREVIAL"
    )
    mail.send(msg)
    return True