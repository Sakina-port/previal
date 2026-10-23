import hashlib
import logging
import os
import re

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

journal = logging.getLogger("previal.stockage")

DOSSIER_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stockage")
NOM_VALIDE = re.compile(r"^[0-9a-f]{32}\.(pdf|jpg|png)$")


class StockageErreur(Exception):
    """Erreur de stockage, avec un message sans détail technique."""


def _mode():
    mode = os.getenv("STOCKAGE_MODE", "s3").strip().lower()
    if mode not in ("s3", "local"):
        raise StockageErreur("STOCKAGE_MODE doit valoir 's3' ou 'local'.")
    return mode


def _verifier_nom(nom_stocke):
    if not NOM_VALIDE.match(nom_stocke or ""):
        raise StockageErreur("Nom de fichier invalide.")


def _echec(action, erreur):
    journal.error("Stockage : échec de %s (%s)", action, erreur)
    raise StockageErreur("Le service de stockage est momentanément indisponible.") from erreur


_client_s3 = None


def _client():
    global _client_s3
    if _client_s3 is None:
        manquantes = [
            nom for nom in ("S3_ENDPOINT_URL", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET")
            if not os.getenv(nom)
        ]
        if manquantes:
            raise StockageErreur("Configuration S3 incomplète : " + ", ".join(manquantes))
        _client_s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name=os.getenv("S3_REGION", "us-east-1"),
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )
    return _client_s3


_bucket_verifie = False


def _assurer_bucket():
    global _bucket_verifie
    if _bucket_verifie:
        return
    bucket = os.getenv("S3_BUCKET")
    client = _client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as erreur:
        code = erreur.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket", "NotFound") and os.getenv("S3_CREER_BUCKET", "0") == "1":
            client.create_bucket(Bucket=bucket)
            journal.info("Stockage : bucket créé.")
        else:
            raise
    _bucket_verifie = True


def verifier_stockage():
    if _mode() == "local":
        os.makedirs(DOSSIER_LOCAL, exist_ok=True)
        return True
    try:
        _assurer_bucket()
    except (ClientError, BotoCoreError) as erreur:
        _echec("vérification", erreur)
    return True


def enregistrer_fichier(contenu, nom_stocke, type_mime=None):
    _verifier_nom(nom_stocke)
    if not isinstance(contenu, (bytes, bytearray)) or len(contenu) == 0:
        raise StockageErreur("Contenu vide.")

    if _mode() == "local":
        try:
            os.makedirs(DOSSIER_LOCAL, exist_ok=True)
            with open(os.path.join(DOSSIER_LOCAL, nom_stocke), "xb") as fichier:
                fichier.write(contenu)
        except OSError as erreur:
            _echec("écriture locale", erreur)
        return

    try:
        _assurer_bucket()
        arguments = {"Bucket": os.getenv("S3_BUCKET"), "Key": nom_stocke, "Body": bytes(contenu)}
        if type_mime:
            arguments["ContentType"] = type_mime
        if os.getenv("S3_CHIFFREMENT", "0") == "1":
            arguments["ServerSideEncryption"] = "AES256"
        _client().put_object(**arguments)
    except (ClientError, BotoCoreError) as erreur:
        _echec("envoi", erreur)


def _lire_local(nom_stocke):
    chemin = os.path.join(DOSSIER_LOCAL, nom_stocke)
    if not os.path.isfile(chemin):
        return None
    with open(chemin, "rb") as fichier:
        return fichier.read()


def lire_fichier(nom_stocke, sha256_attendu=None):
    _verifier_nom(nom_stocke)
    contenu = None

    if _mode() == "local":
        try:
            contenu = _lire_local(nom_stocke)
        except OSError as erreur:
            _echec("lecture locale", erreur)
    else:
        try:
            reponse = _client().get_object(Bucket=os.getenv("S3_BUCKET"), Key=nom_stocke)
            contenu = reponse["Body"].read()
        except ClientError as erreur:
            code = erreur.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                # Reprise des anciens documents rangés dans le dossier local
                contenu = _lire_local(nom_stocke)
                if contenu is None:
                    raise StockageErreur("Fichier introuvable.") from erreur
                journal.warning("Stockage : document lu depuis l'ancien dossier local.")
            else:
                _echec("lecture", erreur)
        except BotoCoreError as erreur:
            _echec("lecture", erreur)

    if contenu is None:
        raise StockageErreur("Fichier introuvable.")

    if sha256_attendu and hashlib.sha256(contenu).hexdigest() != sha256_attendu:
        journal.error("Stockage : empreinte différente pour %s", nom_stocke)
        raise StockageErreur("Le fichier est corrompu ou a été modifié.")

    return contenu

def supprimer_fichier(nom_stocke):
    _verifier_nom(nom_stocke)
    if _mode() == "local":
        try:
            os.remove(os.path.join(DOSSIER_LOCAL, nom_stocke))
        except FileNotFoundError:
            pass
        except OSError as erreur:
            _echec("suppression locale", erreur)
        return
    try:
        _client().delete_object(Bucket=os.getenv("S3_BUCKET"), Key=nom_stocke)
    except (ClientError, BotoCoreError) as erreur:
        _echec("suppression", erreur)

    chemin_local = os.path.join(DOSSIER_LOCAL, nom_stocke)
    if os.path.isfile(chemin_local):
        try:
            os.remove(chemin_local)
        except OSError as erreur:
            _echec("suppression locale", erreur)

_client_public_s3 = None


def _client_public():
    global _client_public_s3
    if _client_public_s3 is None:
        _client_public_s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_PUBLIC_URL") or os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name=os.getenv("S3_REGION", "us-east-1"),
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    return _client_public_s3

def adresse_temporaire(nom_stocke, duree_secondes=60, nom_telechargement=None, type_mime=None):
    _verifier_nom(nom_stocke)
    if _mode() == "local":
        raise StockageErreur("Adresse temporaire indisponible en mode local.")
    duree = max(1, min(int(duree_secondes), 300))
    parametres = {"Bucket": os.getenv("S3_BUCKET"), "Key": nom_stocke}
    if type_mime:
        parametres["ResponseContentType"] = type_mime
    if nom_telechargement:
        propre = re.sub(r"[^A-Za-z0-9._-]", "_", nom_telechargement)[:100]
        parametres["ResponseContentDisposition"] = f'inline; filename="{propre}"'
    try:
            return _client_public().generate_presigned_url("get_object", Params=parametres, ExpiresIn=duree)
    except (ClientError, BotoCoreError) as erreur:
        _echec("création de l'adresse temporaire", erreur)
def existe_dans_bucket(nom_stocke):
    _verifier_nom(nom_stocke)
    if _mode() == "local":
        return False
    try:
        _client().head_object(Bucket=os.getenv("S3_BUCKET"), Key=nom_stocke)
        return True
    except ClientError as erreur:
        code = erreur.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        _echec("vérification d'existence", erreur)
    except BotoCoreError as erreur:
        _echec("vérification d'existence", erreur)
        