from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Utilisateur(db.Model, UserMixin):
    __tablename__ = 'utilisateurs'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    email = db.Column(db.String(200), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='client')
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)


class Produit(db.Model):
    __tablename__ = 'produits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    categorie = db.Column(db.String(100))
    formulaire_schema = db.Column(db.JSON)


class Dossier(db.Model):
    __tablename__ = 'dossiers'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'))
    statut = db.Column(db.String(50), default='en_cours')
    source = db.Column(db.String(50), default='interne')
    reponses = db.Column(db.JSON)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)


class Devis(db.Model):
    __tablename__ = 'devis'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'))
    montant = db.Column(db.Float)
    provider = db.Column(db.String(50), default='interne')
    payload_brut = db.Column(db.JSON)
    fichier_pdf = db.Column(db.String(255))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

class Contrat(db.Model):
    __tablename__ = 'contrats'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'))
    fichier_pdf = db.Column(db.String(255))
    source = db.Column(db.String(50), default='interne')
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)


class Attestation(db.Model):
    __tablename__ = 'attestations'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'))
    fichier_pdf = db.Column(db.String(255))
    date_envoi_email = db.Column(db.DateTime)


class Signature(db.Model):
    __tablename__ = 'signatures'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'))
    statut = db.Column(db.String(50), default='en_attente')
    provider = db.Column(db.String(50), default='interne')
    fichier_signature = db.Column(db.String(255))
    date_signature = db.Column(db.DateTime)


class Grossiste(db.Model):
    __tablename__ = 'grossistes'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    cle_api = db.Column(db.String(255))
    actif = db.Column(db.Boolean, default=False)