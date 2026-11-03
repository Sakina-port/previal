"""Préparation de la connexion MySQL à partir de DATABASE_URL.

- Accepte l'URL telle que la donne l'hébergeur (mysql://...?ssl-mode=REQUIRED)
  et la convertit au format SQLAlchemy/PyMySQL (mysql+pymysql://...).
- Active TLS quand l'URL le demande (ssl-mode), quand un certificat CA est
  fourni (DATABASE_SSL_CA) ou quand l'application tourne sur Vercel.
- Sans ces conditions (PC local, Docker), le comportement ne change pas.
"""
import os
import ssl

from sqlalchemy.engine import make_url

PARAMETRES_SSL_MODE = ("ssl-mode", "ssl_mode", "sslmode")


class ConfigurationBaseErreur(RuntimeError):
    pass


def _contexte_tls(mode, certificat_ca):
    if certificat_ca:
        # Accepte un PEM multiligne ou collé avec des "\n" littéraux.
        contexte = ssl.create_default_context(cadata=certificat_ca.replace("\\n", "\n"))
        contexte.check_hostname = mode != "VERIFY_CA"
        return contexte
    contexte = ssl.create_default_context()
    if mode == "REQUIRED":
        # ssl-mode=REQUIRED (sens MySQL) : connexion chiffrée sans vérification
        # du certificat. Fournir DATABASE_SSL_CA pour une vérification complète.
        contexte.check_hostname = False
        contexte.verify_mode = ssl.CERT_NONE
    return contexte


def configurer_base(url_brute, environ=os.environ):
    """Retourne (uri_sqlalchemy, options_moteur)."""
    if not url_brute or not url_brute.strip():
        raise ConfigurationBaseErreur(
            "DATABASE_URL n'est pas définie. Sur Vercel : Settings > Environment "
            "Variables > ajouter DATABASE_URL (Production), puis redéployer."
        )

    url_texte = url_brute.strip()
    if url_texte.startswith("mysql://"):
        url_texte = "mysql+pymysql://" + url_texte[len("mysql://"):]

    try:
        url = make_url(url_texte)
    except Exception as erreur:
        raise ConfigurationBaseErreur("DATABASE_URL n'a pas un format d'URL valide.") from erreur

    mode = None
    requete = dict(url.query)
    for cle in PARAMETRES_SSL_MODE:
        if cle in requete:
            mode = str(requete.pop(cle)).upper()
    url = url.set(query=requete)

    options = {}
    if url.get_backend_name() != "mysql":
        return url.render_as_string(hide_password=False), options

    options = {"pool_pre_ping": True, "pool_recycle": 280}
    certificat_ca = environ.get("DATABASE_SSL_CA", "").strip()
    sur_vercel = environ.get("VERCEL") == "1"

    if mode == "DISABLED":
        if sur_vercel:
            raise ConfigurationBaseErreur("ssl-mode=DISABLED est refusé sur Vercel : la base doit utiliser TLS.")
        return url.render_as_string(hide_password=False), options

    if mode or certificat_ca or sur_vercel:
        # Avec un CA fourni, le certificat est toujours vérifié.
        options["connect_args"] = {"ssl": _contexte_tls(mode or "VERIFY_IDENTITY", certificat_ca)}

    return url.render_as_string(hide_password=False), options
