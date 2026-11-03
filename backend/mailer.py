import os
import base64
from html import escape
from flask_mail import Mail, Message


mail = Mail()

# Symbole du logo PREVIAL (image PNG écrite en texte : aucun fichier à ajouter)
LOGO_PNG_B64 = (
    "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"
)


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
<body style="margin:0; padding:0; background:#F3F8F7;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F3F8F7; padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px; width:100%; background:#FFFFFF; border-radius:10px; font-family:Arial, Helvetica, sans-serif; color:#1F2933;">
          <tr>
            <td style="background:#0B4A57; padding:20px 24px; border-radius:10px 10px 0 0;">
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding-right:14px; vertical-align:middle;"><img src="cid:logo-previal" width="60" height="47" alt="" style="display:block; border:0;"></td>
                  <td style="vertical-align:middle;">
                    <div style="font-size:24px; font-weight:bold; letter-spacing:1px; line-height:1; color:#E3B045;">PREVIAL</div>
                    <div style="margin-top:6px; font-size:10px; letter-spacing:3px; text-transform:uppercase; color:#D2E8E6;">Protection &amp; sérénité</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr><td style="height:4px; line-height:4px; font-size:0; background:#E3B045;">&nbsp;</td></tr>
          <tr>
            <td style="padding:28px 24px 24px 24px; font-size:15px; line-height:1.55;">
              <h1 style="margin:0 0 16px 0; font-size:21px; line-height:1.25; color:#0B4A57;">Documents à nous transmettre</h1>
              <p style="margin:0 0 14px 0;">Bonjour,</p>
              <p style="margin:0 0 14px 0;">Pour avancer sur votre dossier <strong>{escape(numero_dossier)}</strong>, merci de nous transmettre les documents suivants :</p>
              <ul style="margin:0 0 22px 0; padding-left:20px;">{liste_html}</ul>
              <table role="presentation" cellpadding="0" cellspacing="0" align="center" style="margin:0 auto 22px auto;">
                <tr>
                  <td align="center" bgcolor="#16776F" style="border-radius:999px;">
                    <a href="{lien_html}" target="_blank" style="display:inline-block; padding:14px 36px; font-size:16px; font-weight:bold; color:#FFFFFF; text-decoration:none; border-radius:999px;">Cliquer ici</a>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 14px 0; font-size:13px; color:#52606D;">Ce lien de dépôt sécurisé est valable <strong>48 heures</strong>.</p>
              <p style="margin:0 0 14px 0; font-size:13px; color:#52606D;"><strong>Merci de ne nous envoyer aucun document médical.</strong></p>
              <p style="margin:0 0 6px 0; font-size:12px; color:#52606D;">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :</p>
              <p style="margin:0 0 20px 0; font-size:12px; word-break:break-all;"><a href="{lien_html}" style="color:#16776F;">{lien_html}</a></p>
              <p style="margin:0;">Cordialement,<br><strong style="color:#0B4A57;">L'équipe PREVIAL</strong></p>
            </td>
          </tr>
          <tr>
            <td style="background:#EAF5F3; padding:16px 24px; border-radius:0 0 10px 10px; font-size:12px; line-height:1.5; color:#52606D;">
              PREVIAL, courtier en assurance · Protection &amp; sérénité<br>
              <a href="mailto:contact@previal.fr" style="color:#16776F;">contact@previal.fr</a>
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
    msg.attach(
        "logo-previal.png", "image/png", base64.b64decode(LOGO_PNG_B64), "inline",
        headers={"Content-ID": "<logo-previal>", "X-Attachment-Id": "logo-previal"}
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