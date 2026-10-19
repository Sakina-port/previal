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
    presentation = db.Column(db.Text)
    garanties = db.Column(db.JSON)
    formulaire_schema = db.Column(db.JSON)


class Dossier(db.Model):
    __tablename__ = 'dossiers'
    id = db.Column(db.Integer, primary_key=True)
    numero_dossier = db.Column(db.String(20), unique=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=True)
    statut = db.Column(db.String(50), default='nouveau')
    source = db.Column(db.String(50), default='interne')
    reponses = db.Column(db.JSON)
    archive = db.Column(db.Boolean, nullable=False, default=False)
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


class Historique(db.Model):
    __tablename__ = 'historique'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)


class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

class DemandeDocuments(db.Model):
    __tablename__ = 'demandes_documents'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'),nullable=False)
    pieces = db.Column(db.JSON, nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=True)
    date_expiration = db.Column(db.DateTime, nullable=True)
    revoquee = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'), nullable= False)
    demande_id = db.Column(db.Integer, db.ForeignKey('demandes_documents.id'), nullable=True)
    categorie = db.Column(db.String(50), nullable=False)
    nom_original = db.Column(db.String(255))
    nom_stocke = db.Column(db.String(100), unique=True, nullable=False)
    type_reel = db.Column(db.String(100))
    taille = db.Column(db.Integer)
    sha256 = db.Column(db.String(64))
    source = db.Column(db.String(30), default='client')
    statut = db.Column(db.String(30), default= 'recu')
    date_suppression_prevue = db.Column(db.DateTime, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

class Rappel(db.Model):
    __tablename__ = 'rappels'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    date_rappel = db.Column(db.DateTime, nullable=False)
    contenu = db.Column(db.String(255), nullable=False)
    fait = db.Column(db.Boolean, default=False)
    date_fait = db.Column(db.DateTime, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

class EtudePartenaire(db.Model):
    __tablename__ = 'etudes_partenaires'
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossiers.id'), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    partenaire = db.Column(db.String(100), nullable=False)
    etat = db.Column(db.String(30), default='a_interroger')
    commentaire = db.Column(db.String(255))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_maj = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)