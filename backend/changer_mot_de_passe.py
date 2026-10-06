from app import app
from models import db, Utilisateur
import bcrypt

with app.app_context():
    email = "contact@previal.fr"
    nouveau_mot_de_passe = "METS_ICI_TON_NOUVEAU_MOT_DE_PASSE"

    utilisateur = Utilisateur.query.filter_by(email=email).first()
    if utilisateur:
        hash_mot_de_passe = bcrypt.hashpw(nouveau_mot_de_passe.encode('utf-8'), bcrypt.gensalt())
        utilisateur.mot_de_passe = hash_mot_de_passe.decode('utf-8')
        db.session.commit()
        print("Mot de passe modifié avec succès.")
    else:
        print("Aucun compte trouvé avec cet e-mail.")