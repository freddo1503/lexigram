# Installation et configuration initiale

Ce tutoriel vous guidera à travers le processus d'installation et de configuration de Lexigram sur votre machine locale.

## Prérequis

Avant de commencer, assurez-vous d'avoir :

- Python 3.12 ou supérieur installé
- Un compte GitHub pour cloner le dépôt
- Un compte développeur Instagram avec accès à l'API
- Un compte Légifrance avec accès à l'API
- Un compte OpenAI pour accéder à DALL·E
- Un compte Mistral AI

## Étape 1 : Cloner le dépôt

Commencez par cloner le dépôt GitHub de Lexigram :

```bash
git clone https://github.com/freddo1503/lexigram.git
cd lexigram
```

## Étape 2 : Configurer l'environnement virtuel

Créez et activez un environnement virtuel Python :

```bash
python -m venv .venv
source .venv/bin/activate  # Sur Windows, utilisez .venv\Scripts\activate
```

## Étape 3 : Installer les dépendances

Installez les dépendances requises :

```bash
pip install -r requirements.txt
```

## Étape 4 : Configurer les variables d'environnement

Créez un fichier `.env` à la racine du projet en vous basant sur le fichier `.env.example` :

```bash
cp .env.example .env
```

Ouvrez le fichier `.env` et remplissez les variables suivantes :

```
# API Keys
OPENAI_API_KEY=votre_clé_api_openai
MISTRAL_API_KEY=votre_clé_api_mistral
LEGIFRANCE_API_KEY=votre_clé_api_legifrance
ACCESS_TOKEN=votre_token_instagram

# DynamoDB Configuration
DYNAMO_TABLE_NAME=lexigram_laws
```

## Étape 5 : Configurer DynamoDB

Si vous utilisez DynamoDB en local pour le développement :

```bash
# Installation de DynamoDB local
mkdir -p ./dynamodb_local
cd ./dynamodb_local
wget https://d1ni2b6xgvw0s0.cloudfront.net/amazon-dynamodb-local-latest.tar.gz
tar -xvf amazon-dynamodb-local-latest.tar.gz
cd ..

# Démarrage de DynamoDB local
java -Djava.library.path=./dynamodb_local/DynamoDBLocal_lib -jar ./dynamodb_local/DynamoDBLocal.jar -sharedDb
```

Dans un autre terminal, créez la table nécessaire :

```bash
python scripts/create_dynamodb_table.py
```

## Étape 6 : Vérifier l'installation

Exécutez le script de test pour vérifier que tout est correctement configuré :

```bash
python scripts/test_installation.py
```

Si tout est correctement configuré, vous devriez voir un message de succès.

## Étape 7 : Exécuter l'application

Vous pouvez maintenant exécuter l'application principale :

```bash
python -m app.main
```

## Dépannage

### Problèmes courants

1. **Erreur d'authentification API** : Vérifiez que vos clés API sont correctement configurées dans le fichier `.env`.
2. **Erreur de connexion à DynamoDB** : Assurez-vous que DynamoDB local est en cours d'exécution ou que vos identifiants AWS sont correctement configurés.
3. **Erreur de version Python** : Vérifiez que vous utilisez Python 3.12 ou supérieur.

### Obtenir de l'aide

Si vous rencontrez des problèmes, vous pouvez :
- Ouvrir une issue sur le [dépôt GitHub](https://github.com/freddo1503/lexigram/issues)
- Consulter la documentation de référence pour plus de détails sur la configuration

## Prochaines étapes

Maintenant que vous avez installé et configuré Lexigram, vous pouvez passer au tutoriel suivant pour [générer votre premier résumé de loi](first-summary.md).