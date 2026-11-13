
import ast
import glob
import re
import sys

from app import app

METHODES = ("POST", "PUT", "PATCH", "DELETE")
echecs = 0


def resultat(ok, texte):
    global echecs
    print(f"  [{'OK ' if ok else 'ECHEC'}] {texte}")
    if not ok:
        echecs += 1


print("1. La protection est-elle active ?")
protegees = set(app.config.get("WTF_CSRF_METHODS", []))
resultat("csrf" in app.extensions, "CSRFProtect est enregistré dans l'application")
resultat(app.config.get("WTF_CSRF_ENABLED", True), "la protection n'est pas désactivée")
resultat(set(METHODES) <= protegees, "les 4 méthodes sont contrôlées : " + ", ".join(sorted(protegees)))

print("\n2. Chaque route qui modifie des données, sans jeton")
client = app.test_client()
nombre = 0
par_methode = {m: 0 for m in METHODES}
for regle in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if regle.endpoint == "static":
        continue
    for methode in METHODES:
        if methode not in regle.methods:
            continue
        adresse = re.sub(r"<[^>]+>", "x", re.sub(r"<int:[^>]+>", "1", regle.rule))
        reponse = client.open(adresse, method=methode)
        nombre += 1
        par_methode[methode] += 1
        resultat(reponse.status_code == 400, f"{methode:6} {regle.rule}  ->  {reponse.status_code}")
print("     Routes contrôlées : " + ", ".join(f"{m} {n}" for m, n in par_methode.items()) + f"  (total {nombre})")

print("\n3. Avec un vrai jeton, la requête passe")
try:
    page = client.get("/")
    jeton = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.get_data(as_text=True))
    resultat(jeton is not None, "la page d'accueil contient un jeton")
    if jeton:
        envoi = client.post("/contact", data={"csrf_token": jeton.group(1)})
        resultat(envoi.status_code == 200, f"POST /contact avec jeton (formulaire vide, rien n'est enregistré)  ->  {envoi.status_code}")
except Exception as erreur:
    resultat(False, f"essai impossible : {erreur}")

print("\n4. Chaque formulaire POST des gabarits")
total = protege = 0
for chemin in sorted(glob.glob("templates/*.html")):
    texte = open(chemin, encoding="utf-8").read()
    formulaires = [(m.start(), m.end()) for m in re.finditer(r'<form\b[^>]*?\bmethod\s*=\s*["\']?post["\']?[^>]*>', texte, re.I)]
    for debut, fin in formulaires:
        total += 1
        suite = texte.find("</form>", fin)
        ok = "csrf_token" in texte[fin:suite if suite != -1 else fin + 600]
        protege += ok
        if not ok:
            resultat(False, f"{chemin} : formulaire sans jeton : {texte[debut:fin][:90]}")
    if formulaires:
        print(f"     {chemin} : {len(formulaires)} formulaire(s) POST")
resultat(total == protege, f"{protege} formulaire(s) POST protégé(s) sur {total}")

print("\n5. Routes accessibles par un simple lien (GET) qui modifieraient des données")
source = open("app.py", encoding="utf-8").read()
suspectes, journal = [], []
for noeud in ast.walk(ast.parse(source)):
    if not isinstance(noeud, ast.FunctionDef):
        continue
    for deco in noeud.decorator_list:
        if isinstance(deco, ast.Call) and getattr(deco.func, "attr", "") == "route":
            methodes = ["GET"]
            for mot in deco.keywords:
                if mot.arg == "methods" and isinstance(mot.value, (ast.List, ast.Tuple)):
                    methodes = [e.value for e in mot.value.elts if isinstance(e, ast.Constant)]
            if "GET" not in methodes or "POST" in methodes:
                continue
            ajouts, supprime, modifie, valide = set(), False, False, False
            for n in ast.walk(noeud):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                    if n.func.attr == "delete":
                        supprime = True
                    if n.func.attr == "commit":
                        valide = True
                    if n.func.attr == "add" and n.args and isinstance(n.args[0], ast.Call) and isinstance(n.args[0].func, ast.Name):
                        ajouts.add(n.args[0].func.id)
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) for t in n.targets):
                    modifie = True
            if supprime or modifie or (ajouts - {"Historique"}):
                suspectes.append(noeud.name)
            elif valide:
                journal.append(noeud.name)
resultat(not suspectes, "aucune route GET ne modifie de données" if not suspectes else "routes GET qui modifient des données : " + ", ".join(suspectes))
if journal:
    print("  [INFO] routes GET qui écrivent seulement dans le journal d'historique (acceptable) : " + ", ".join(journal))

print("\n" + "-" * 60)
print("Tout est en ordre." if not echecs else f"{echecs} problème(s) à corriger.")
sys.exit(1 if echecs else 0)