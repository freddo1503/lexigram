# Agents IA

Cette page documente les agents d'intelligence artificielle utilisés dans Lexigram pour traiter et transformer les textes législatifs en contenu Instagram.

## Vue d'ensemble

Lexigram utilise une architecture multi-agents basée sur la bibliothèque [CrewAI](https://github.com/joaomdmoura/crewAI). Chaque agent est spécialisé dans une tâche spécifique et ils travaillent ensemble pour produire le résultat final.

## AnalysteJuridique

L'AnalysteJuridique est responsable de l'analyse et du résumé des textes juridiques.

### Rôle et objectif

```python
role="Analyste Juridique Expert"
goal="Analyser et synthétiser des textes juridiques complexes avec précision et clarté"
```

### Fonctionnalités principales

- Analyse des textes juridiques bruts
- Extraction des points clés et des implications
- Génération de résumés structurés et précis

### Paramètres de configuration

| Paramètre | Description | Valeur par défaut |
|-----------|-------------|-------------------|
| `llm` | Modèle de langage utilisé | `gpt-4` |
| `allow_delegation` | Autorisation de déléguer des tâches | `False` |
| `verbose` | Mode verbeux pour le débogage | `True` |

### Exemple d'utilisation

```python
from app.agents.lex_analyst import AnalysteJuridique
from app.agents.task import text_summary

analyst = AnalysteJuridique()
text_summary.agent = analyst
result = analyst.execute_task(text_summary, {
    "titre": "Loi n° 2023-123 du 15 février 2023",
    "date_publication": "16 février 2023",
    "signataires": "Le Président de la République\nLe Premier ministre",
    "contenu": "Article 1 - Les dispositions suivantes sont applicables..."
})
```

## LexPictor

LexPictor est responsable de la génération d'images basées sur le contenu juridique analysé.

### Rôle et objectif

```python
role="Artiste Visuel Innovant"
goal="Créer des oeuvres d'art visuelles captivantes et originales en utilisant des techniques numériques avancées"
```

### Fonctionnalités principales

- Génération d'images via DALL·E
- Création de prompts visuels basés sur l'analyse juridique
- Optimisation des images pour Instagram

### Outils intégrés

LexPictor utilise l'outil `DallETool` pour générer des images via l'API OpenAI.

#### DallETool

| Paramètre | Description |
|-----------|-------------|
| `name` | "Dall-E Tool" |
| `description` | "Generates images using OpenAI's Dall-E model." |
| `args_schema` | `ImagePromptSchema` |

### Exemple d'utilisation

```python
from app.agents.lex_pictor import LexPictor
from app.agents.task import image_generation

pictor = LexPictor()
image_generation.agent = pictor
result = pictor.execute_task(image_generation, {
    "context": "Résumé d'une loi sur la protection de l'environnement..."
})
```

### Schéma de sortie

```python
class ImagePayload(BaseModel):
    image_url: str
    image_description: str
```

## LexMarker

LexMarker est responsable de la création de légendes Instagram engageantes basées sur le contenu juridique.

### Rôle et objectif

```python
role="Expert en Marketing de Contenu"
goal="Créer des légendes Instagram engageantes et informatives"
```

### Fonctionnalités principales

- Transformation du contenu juridique en texte accessible
- Optimisation pour l'engagement sur Instagram
- Formatage adapté aux contraintes de la plateforme

### Exemple d'utilisation

```python
from app.agents.lex_marketer import LexMarker
from app.agents.task import caption

marketer = LexMarker()
caption.agent = marketer
result = marketer.execute_task(caption, {
    "context": "Résumé d'une loi sur la protection de l'environnement..."
})
```

## Orchestration avec Crew

Les agents sont orchestrés via la classe `Crew` qui gère leur interaction et le flux de travail.

### Création de l'équipage

```python
from app.agents.crew import create_crew

crew = create_crew()
result = crew.kickoff(
    inputs={
        "titre": "Loi n° 2023-123 du 15 février 2023",
        "date_publication": "16 février 2023",
        "signataires": "Le Président de la République\nLe Premier ministre",
        "contenu": "Article 1 - Les dispositions suivantes sont applicables..."
    }
)
```

### Flux de travail

1. L'AnalysteJuridique analyse et résume le texte juridique
2. LexPictor génère une image basée sur le résumé
3. LexMarker crée une légende Instagram basée sur le résumé

## Voir aussi

- [Architecture multi-agents](../explanation/multi-agent-architecture.md)
- [API OpenAI (DALL·E)](openai-api.md)
- [API Mistral AI](mistral-api.md)