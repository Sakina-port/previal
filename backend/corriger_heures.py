"""
Met app.py à l'heure de Paris (à lancer UNE SEULE FOIS, dans le dossier backend).
Une copie de ton fichier est faite avant : app.py.avant-heures
Si une ligne n'est pas trouvée, RIEN n'est modifié.
"""
import shutil
import sys

CHANGEMENTS = [
    ("EtudePartenaire, JournalConnexion",
     "EtudePartenaire, JournalConnexion, maintenant_paris", 1),
    ("datetime.utcnow()",
     "maintenant_paris()", 8),
    ('valeur.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Paris")).strftime(format)',
     "valeur.strftime(format)", 1),
    ("fin_aujourdhui = demain_paris.astimezone(timezone.utc).replace(tzinfo=None)",
     "fin_aujourdhui = demain_paris.replace(tzinfo=None)", 1),
    ('date_utc = date_locale.replace(tzinfo=ZoneInfo("Europe/Paris")).astimezone(timezone.utc).replace(tzinfo=None)',
     "date_utc = date_locale", 1),
    ('return valeur.strftime("%Y-%m-%d %H:%M:%S") + " UTC" if valeur else None',
     'return valeur.strftime("%Y-%m-%d %H:%M:%S") if valeur else None', 1),
    ('"remarque": "Les dates sont en heure UTC, sauf consentement_date (heure de Paris)."',
     '"remarque": "Toutes les dates sont en heure de Paris."', 1),
]

with open("app.py", encoding="utf-8") as f:
    texte = f.read()

if "maintenant_paris()" in texte:
    print("app.py contient déjà maintenant_paris() : le programme a déjà été lancé. Rien n'a été modifié.")
    sys.exit(0)

problemes = []
for ancien, nouveau, attendu in CHANGEMENTS:
    trouve = texte.count(ancien)
    etat = "OK " if trouve == attendu else "PROBLEME"
    print(f"[{etat}] trouvé {trouve} fois (attendu {attendu}) : {ancien[:70]}")
    if trouve != attendu:
        problemes.append(ancien)

if problemes:
    print("\nRIEN n'a été modifié. Copie ces lignes et envoie-les moi.")
    sys.exit(1)

shutil.copyfile("app.py", "app.py.avant-heures")
for ancien, nouveau, attendu in CHANGEMENTS:
    texte = texte.replace(ancien, nouveau)
with open("app.py", "w", encoding="utf-8", newline="") as f:
    f.write(texte)

print("\nTERMINÉ : app.py est à l'heure de Paris. Copie de sécurité : app.py.avant-heures")