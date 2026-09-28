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


def envoyer_documents(destinataire, produit_nom, dossier_id, chemin_devis, chemin_contrat):
    if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD'):
        print(f"[E-MAIL NON ENVOYÉ] Configuration manquante dans .env. Destinataire prévu : {destinataire}")
        return False

    msg = Message(
        subject=f"Prévial — Votre contrat {produit_nom}",
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