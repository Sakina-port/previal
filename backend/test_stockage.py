import hashlib
import uuid

from dotenv import load_dotenv

load_dotenv()

import stockage
from stockage import StockageErreur

nom = uuid.uuid4().hex + ".pdf"
contenu = b"%PDF-1.4 fichier de test PREVIAL"
empreinte = hashlib.sha256(contenu).hexdigest()

print("1. Vérification du stockage (crée le bucket si besoin)...")
stockage.verifier_stockage()
print("   OK")

print("2. Envoi d'un fichier de test...")
stockage.enregistrer_fichier(contenu, nom, "application/pdf")
print("   OK")

print("3. Lecture avec vérification de l'empreinte...")
assert stockage.lire_fichier(nom, empreinte) == contenu
print("   OK")

print("4. Une mauvaise empreinte doit être refusée...")
try:
    stockage.lire_fichier(nom, "0" * 64)
    print("   ERREUR : aurait dû être refusé")
except StockageErreur as erreur:
    print("   OK :", erreur)

print("5. Un nom dangereux doit être refusé...")
try:
    stockage.lire_fichier("../.env")
    print("   ERREUR : aurait dû être refusé")
except StockageErreur as erreur:
    print("   OK :", erreur)

print("6. Adresse temporaire...")
print("   OK :", stockage.adresse_temporaire(nom)[:45] + "...")

print("7. Suppression, puis lecture impossible...")
stockage.supprimer_fichier(nom)
try:
    stockage.lire_fichier(nom)
    print("   ERREUR : le fichier existe encore")
except StockageErreur as erreur:
    print("   OK :", erreur)