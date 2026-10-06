from app import app
from models import db, Utilisateur
import bcrypt

with app.app_context():
    email = "contact@previal.fr"
    mot_de_passe = "XXX"

    existe_deja = Utilisateur.query.filter_by(email=email).first()
    if existe_deja:
        print("Ce compte existe déjà.")
    else:
        hash_mot_de_passe = bcrypt.hashpw(mot_de_passe.encode('utf-8'), bcrypt.gensalt())
        nouvel_admin = Utilisateur(
            nom="Madzous",
            prenom="Eric",
            email=email,
            mot_de_passe=hash_mot_de_passe.decode('utf-8'),
            role="admin"
        )
        db.session.add(nouvel_admin)
        db.session.commit()
        print("Compte admin créé avec succès.")
