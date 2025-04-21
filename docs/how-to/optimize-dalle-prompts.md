# Optimiser les prompts pour DALL·E

Ce guide vous montre comment optimiser les prompts envoyés à DALL·E pour générer des images plus pertinentes et visuellement attrayantes pour vos publications Instagram sur les lois françaises.

## Objectifs

- Améliorer la qualité des images générées
- Assurer la pertinence des images par rapport au contenu juridique
- Optimiser l'utilisation de l'API DALL·E

## Comprendre le contexte

Avant de modifier les prompts, il est important de comprendre comment LexPictor (l'agent responsable de la génération d'images) fonctionne avec DALL·E :

1. LexPictor reçoit un résumé juridique de l'AnalysteJuridique
2. Il génère un prompt descriptif pour DALL·E
3. DALL·E crée une image basée sur ce prompt
4. L'image est utilisée pour la publication Instagram

## Étapes pour optimiser les prompts

### 1. Modifier le template de prompt

Le template de prompt se trouve dans la classe `DallETool` dans le fichier `app/agents/lex_pictor.py`. Vous pouvez personnaliser la façon dont les prompts sont générés en modifiant la méthode `_run` :

```python
def _run(self, **kwargs) -> ImagePayload | str:
    # Personnalisez la génération du prompt ici
    image_description = kwargs.get("image_description")
    
    # Ajoutez des éléments au prompt pour améliorer la qualité
    enhanced_prompt = f"""
    Créez une image professionnelle et élégante représentant : {image_description}
    
    Style : Minimaliste, moderne, avec des couleurs douces
    Contexte : Juridique, législatif, officiel
    Public : Utilisateurs Instagram intéressés par l'actualité juridique
    Ne pas inclure : Texte, logos, drapeaux nationaux
    """
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=enhanced_prompt,
        size="1024x1024",
        n=1,
    )
    
    return ImagePayload(
        image_url=response.data[0].url,
        image_description=response.data[0].revised_prompt,
    )
```

### 2. Ajouter des éléments visuels spécifiques

Pour améliorer la cohérence visuelle de vos publications, ajoutez des éléments spécifiques à vos prompts :

```python
# Exemples d'éléments visuels à inclure dans vos prompts
elements_visuels = {
    "environnement": "éléments naturels, feuilles vertes, eau claire",
    "finance": "graphiques élégants, symboles monétaires stylisés",
    "santé": "symboles médicaux, formes organiques, tons bleus apaisants",
    "travail": "outils professionnels, environnement de bureau moderne",
    "éducation": "livres, symboles d'apprentissage, tons chaleureux"
}

# Détectez la catégorie du texte juridique et ajoutez les éléments correspondants
categorie = detecter_categorie(resume_juridique)
elements = elements_visuels.get(categorie, "symboles juridiques, balance de la justice")

enhanced_prompt = f"""
Créez une image professionnelle représentant : {image_description}
Incluez ces éléments visuels : {elements}
"""
```

### 3. Utiliser des modificateurs de style

DALL·E répond bien à certains modificateurs de style qui peuvent améliorer la qualité visuelle :

```python
modificateurs_style = [
    "style minimaliste",
    "illustration vectorielle moderne",
    "design épuré avec palette limitée",
    "composition équilibrée",
    "style infographique professionnel",
    "rendu 3D subtil",
]

# Choisissez aléatoirement un ou deux modificateurs
import random
style_choisi = ", ".join(random.sample(modificateurs_style, 2))

enhanced_prompt = f"""
Créez une image professionnelle représentant : {image_description}
Style visuel : {style_choisi}
"""
```

### 4. Éviter les éléments problématiques

Certains éléments peuvent poser problème dans les images générées :

```python
elements_a_eviter = """
- Pas de texte ou de mots visibles dans l'image
- Éviter les représentations de personnes identifiables
- Pas de symboles nationaux spécifiques (drapeaux, emblèmes)
- Pas de logos ou de marques commerciales
- Éviter les symboles religieux
"""

enhanced_prompt = f"""
Créez une image professionnelle représentant : {image_description}
Restrictions importantes : {elements_a_eviter}
"""
```

### 5. Tester et itérer

Créez un script pour tester différentes variations de prompts :

```python
# Exemple de script de test dans scripts/test_dalle_prompts.py
from app.agents.lex_pictor import DallETool
from app.models.lex_pictor import ImagePayload

# Texte juridique de test
test_summary = "Nouvelle loi sur la protection des données personnelles"

# Variations de prompts à tester
prompt_variations = [
    f"Image représentant {test_summary}",
    f"Illustration conceptuelle de {test_summary}, style minimaliste",
    f"Représentation visuelle abstraite de {test_summary}, tons bleus, style professionnel",
    # Ajoutez d'autres variations
]

# Tester chaque variation
results = []
dalle_tool = DallETool()
for prompt in prompt_variations:
    result = dalle_tool._run(image_description=prompt)
    results.append({
        "prompt": prompt,
        "image_url": result.image_url,
        "revised_prompt": result.image_description
    })

# Enregistrer les résultats pour comparaison
import json
with open("prompt_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

## Exemples de prompts efficaces

Voici quelques exemples de prompts qui ont donné de bons résultats :

### Pour une loi environnementale

```
Créez une image professionnelle représentant une nouvelle législation sur la protection des écosystèmes marins.
Style : Illustration vectorielle moderne avec dégradés doux
Éléments à inclure : Océan stylisé, formes marines abstraites, tons bleus et verts
Ambiance : Sérieuse mais optimiste, institutionnelle
Ne pas inclure : Texte, logos, personnes identifiables, drapeaux
```

### Pour une loi financière

```
Créez une image professionnelle représentant une réforme fiscale pour les petites entreprises.
Style : Design minimaliste avec lignes épurées
Éléments à inclure : Graphiques stylisés, symboles d'entreprise abstraits, palette de couleurs limitée
Ambiance : Professionnelle, claire, institutionnelle
Ne pas inclure : Texte, logos, personnes identifiables, drapeaux
```

## Bonnes pratiques

- **Soyez spécifique** : Plus le prompt est précis, meilleur sera le résultat
- **Équilibrez la créativité et la pertinence** : L'image doit être créative mais rester pertinente par rapport au sujet juridique
- **Maintenez une cohérence visuelle** : Utilisez des éléments de style cohérents entre vos publications
- **Évitez le jargon technique** : DALL·E comprend mieux les descriptions visuelles que les termes juridiques techniques
- **Testez régulièrement** : Les performances de DALL·E évoluent, testez régulièrement de nouvelles approches

## Résolution des problèmes courants

| Problème | Solution |
|----------|----------|
| Images trop génériques | Ajoutez plus de détails spécifiques dans le prompt |
| Images trop complexes | Simplifiez le prompt et spécifiez "style minimaliste" |
| Texte indésirable dans l'image | Ajoutez explicitement "sans texte" dans le prompt |
| Images inappropriées | Utilisez des termes plus neutres et évitez les sujets sensibles |
| Incohérence de style | Créez une liste de modificateurs de style standard à réutiliser |

## Voir aussi

- [API OpenAI (DALL·E)](../reference/openai-api.md) - Documentation technique de l'API DALL·E
- [LexPictor](../reference/agents.md#lexpictor) - Documentation de l'agent de génération d'images
- [Architecture multi-agents](../explanation/multi-agent-architecture.md) - Explication de l'architecture