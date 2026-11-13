"""
VÉRIFICATION DE LA LIMITATION DES TENTATIVES DE CONNEXION

Lancer dans le dossier backend :   python verifier_limitation.py

Les tentatives de test utilisent une adresse e-mail qui n'existe pas (essai-limitation@example.invalid) :
elles apparaissent dans le journal des connexions comme des échecs, sans autre effet.
Les compteurs du test sont remis à zéro à la fin.
"""
import re
import sys

from app import app, limiter

ADRESSE_ESSAI = "essai-limitation@example.invalid"
echecs = 0


def resultat(ok, texte):
    global echecs
    print(f"  [{'OK ' if ok else 'ECHEC'}] {texte}")
    if not ok:
        echecs += 1


def jeton(client, chemin):
    page = client.get(chemin)
    trouve = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.get_data(as_text=True))
    return page.status_code, (trouve.group(1) if trouve else None)


def tenter(client, chemin, jeton_csrf, adresse_ip=None):
    donnees = {"email": ADRESSE_ESSAI, "mot_de_passe": "mot-de-passe-faux", "csrf_token": jeton_csrf}
    if adresse_ip:
        return client.post(chemin, data=donnees, environ_overrides={"REMOTE_ADDR": adresse_ip})
    return client.post(chemin, data=donnees)


def verifier_route(chemin, nom):
    print(f"\n{nom} ({chemin})")
    client = app.test_client()
    statut, csrf = jeton(client, chemin)
    if statut == 404:
        print("  [INFO] route désactivée (404) : non testée")
        return
    resultat(csrf is not None, "le formulaire contient le jeton CSRF")
    if not csrf:
        return
    reponses = [tenter(client, chemin, csrf) for _ in range(6)]
    codes = [r.status_code for r in reponses]
    resultat(codes[:5] == [200] * 5, f"les 5 premières tentatives sont traitées normalement : {codes[:5]}")
    resultat(codes[5] == 429, f"la 6e tentative en moins d'une minute est bloquée : {codes[5]}")
    texte_erreur = reponses[0].get_data(as_text=True)
    texte_blocage = reponses[5].get_data(as_text=True)
    resultat("Identifiants incorrects" in texte_erreur or "incorrect" in texte_erreur.lower(), "l'échec affiche un message d'erreur")
    interdits = ("n'existe pas", "inconnu", "introuvable", "aucun compte", "inexistant", "pas de compte")
    resultat(not any(m in texte_erreur.lower() for m in interdits), "le message d'échec est générique (il ne dit pas si l'e-mail existe)")
    resultat("Trop de tentatives" in texte_blocage, "le blocage affiche « Trop de tentatives »")
    resultat(reponses[5].headers.get("Retry-After") is not None, f"la réponse indique le délai d'attente (Retry-After : {reponses[5].headers.get('Retry-After')} s)")
    autre = app.test_client()
    _, csrf2 = jeton(autre, chemin)
    rep = tenter(autre, chemin, csrf2, adresse_ip="10.20.30.40")
    resultat(rep.status_code == 200, f"un autre visiteur (autre adresse IP) n'est pas bloqué : {rep.status_code}")
    limiter.reset()


print("1. La limitation est-elle installée ?")
resultat(limiter is not None, "Flask-Limiter est enregistré dans l'application")
verifier_route("/equipe", "2. Connexion de l'équipe")
verifier_route("/compte", "3. Connexion client (fonction masquée)")
limiter.reset()

print("\n" + "-" * 60)
print("Tout est en ordre." if not echecs else f"{echecs} problème(s) à corriger.")
sys.exit(1 if echecs else 0)