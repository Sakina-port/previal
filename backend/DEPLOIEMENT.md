# Lancer PREVIAL avec Docker

## Prérequis
- Docker Desktop ouvert (pastille verte « Engine running »).
- Un fichier `.env.docker` dans le dossier `backend` (jamais sur GitHub).

## Démarrer
    docker compose --env-file .env.docker up -d --build

## Premier démarrage seulement
    docker compose --env-file .env.docker exec site python seed.py
    docker compose --env-file .env.docker exec site python creer_admin.py

## Vérifier
    docker compose --env-file .env.docker ps
Les trois services (site, mysql, minio) doivent être « Up ».
Site : http://127.0.0.1:5000 · Espace équipe : /equipe

## Arrêter (les données sont conservées)
    docker compose --env-file .env.docker down

## Retour arrière si une mise à jour échoue
1. Arrêter : commande « Arrêter » ci-dessus.
2. Revenir à la version précédente du code :
       git log --oneline
       git checkout NUMERO_DU_COMMIT_PRECEDENT
3. Relancer : commande « Démarrer ».
4. Si la base est abîmée : restaurer la sauvegarde de MySQL (voir ci-dessous).

## Sauvegarder la base
    docker compose --env-file .env.docker exec mysql sh -c "mysqldump -uroot -p$MYSQL_ROOT_PASSWORD previal" > sauvegarde.sql

## En production
Les mêmes conteneurs sont déployés chez l'hébergeur (OVHcloud ou Scaleway).
Seules changent les valeurs du fichier de configuration : adresse de la base,
adresse et clés du bucket S3, mots de passe.