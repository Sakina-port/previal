import os
from html import escape
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
    adresse_equipe = os.getenv('ADRESSE_EQUIPE')
    if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD') or not adresse_equipe:
        print(f"[E-MAIL NON ENVOYÉ] Notification équipe pour {numero_dossier}")
        return False
    texte_commentaire = commentaire if commentaire else "Aucun commentaire laissé"

    msg = Message(
        subject=f"PREVIAL - Nouvelle demande {numero_dossier}",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[adresse_equipe],
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

    liste_texte = "\n".join(f"- {p}" for p in pieces)
    texte = (
        f"Bonjour,\n\n"
        f"Pour avancer sur votre dossier {numero_dossier}, merci de nous transmettre les documents suivants :\n"
        f"{liste_texte}\n\n"
        f"Vous pouvez les déposer de façon sécurisée avec ce lien, valable 48 heures :\n{lien}\n\n"
        f"Merci de ne nous envoyer aucun document médical.\n\n"
        f"Cordialement,\nL'équipe PREVIAL"
    )

    liste_html = "".join(f"<li style=\"margin:0 0 4px 0;\">{escape(p)}</li>" for p in pieces)
    lien_html = escape(lien, quote=True)
    html = f"""<!DOCTYPE html>
<html lang="fr">
<body style="margin:0; padding:0; background:#F4F6F8;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F6F8; padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px; width:100%; background:#FFFFFF; border-radius:8px; font-family:Arial, Helvetica, sans-serif; color:#1F2933;">
          <tr>
            <td style="background:#12304D; color:#FFFFFF; padding:18px 24px; font-size:18px; font-weight:bold; border-radius:8px 8px 0 0;">PREVIAL</td>
          </tr>
          <tr>
            <td style="padding:24px; font-size:15px; line-height:1.5;">
              <p style="margin:0 0 14px 0;">Bonjour,</p>
              <p style="margin:0 0 14px 0;">Pour avancer sur votre dossier <strong>{escape(numero_dossier)}</strong>, merci de nous transmettre les documents suivants :</p>
              <ul style="margin:0 0 20px 0; padding-left:20px;">{liste_html}</ul>
              <table role="presentation" cellpadding="0" cellspacing="0" align="center" style="margin:0 auto 20px auto;">
                <tr>
                  <td align="center" bgcolor="#1E6FB8" style="border-radius:6px;">
                    <a href="{lien_html}" target="_blank" style="display:inline-block; padding:14px 32px; font-size:16px; font-weight:bold; color:#FFFFFF; text-decoration:none; border-radius:6px;">Cliquer ici</a>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 14px 0; font-size:13px; color:#5F5E5A;">Ce lien de dépôt sécurisé est valable <strong>48 heures</strong>.</p>
              <p style="margin:0 0 14px 0; font-size:13px; color:#5F5E5A;"><strong>Merci de ne nous envoyer aucun document médical.</strong></p>
              <p style="margin:0 0 6px 0; font-size:12px; color:#5F5E5A;">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :</p>
              <p style="margin:0 0 18px 0; font-size:12px; word-break:break-all;"><a href="{lien_html}" style="color:#1E6FB8;">{lien_html}</a></p>
              <p style="margin:0;">Cordialement,<br>L'équipe PREVIAL</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    msg = Message(
        subject=f"PREVIAL - Documents à nous transmettre ({numero_dossier})",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[destinataire],
        body=texte,
        html=html
    )
    mail.send(msg)
    return True


def notifier_equipe_depot(numero_dossier, pieces):
    adresse_equipe = os.getenv('ADRESSE_EQUIPE')
    if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD') or not adresse_equipe:
        print(f"[E-MAIL NON ENVOYÉ] Dépot de documents sur {numero_dossier}")
        return False
    liste_pieces = "\n".join(f"- {p}" for p in pieces)
    msg = Message(
        subject=f"PREVIAL - Documents reçus ({numero_dossier})",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[adresse_equipe],
        body=f"Un client a déposé des documents pour le dossier {numero_dossier} :\n{liste_pieces}\n\nConsultez l'espace privé pour les ouvrir."
    )
    mail.send(msg)
    return True