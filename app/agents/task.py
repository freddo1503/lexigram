"""
Task definitions for the Lexigram application.

This module defines the tasks used by the agents in the Lexigram application.
Each task is responsible for a specific part of the legal text processing pipeline:
- text_summary: Analyzes legal text and produces a structured summary
- image_generation: Creates a professional image based on the legal text
- caption: Converts legal analysis into an Instagram-friendly post
"""

import re
from typing import Tuple

from crewai import Task
from crewai.tasks.task_output import TaskOutput

from app.models.lex_pictor import ImagePayload


def get_task_description() -> str:
    """
    Get the description for the text summary task.

    Returns:
        str: The task description with placeholders for title, publication date,
             signatories, and content.
    """
    return (
        "Analyser le texte juridique fourni et produire un résumé structuré sans omettre d'informations essentielles. "
        "Le résumé doit conserver l'intégralité des éléments clés tout en étant clair et bien organisé. Il doit inclure :\n"
        "1. Titre officiel du texte juridique : {titre}\n"
        "2. Date de publication (format : jour mois année) : {date_publication}\n"
        "3. Signataires officiels : {signataires}\n"
        "4. Analyse détaillée de chaque article du texte juridique, en identifiant clairement le numéro ou l'identifiant de chaque article, "
        "suivie d'une synthèse de son contenu et de ses implications : {contenu}"
    )


def get_expected_output() -> str:
    """
    Get the expected output format for the text summary task.

    Returns:
        str: The expected output format description.
    """
    return (
        "Un résumé structuré comprenant :\n"
        "- Le titre officiel du texte juridique\n"
        "- La date de publication au format jour mois année\n"
        "- La liste des signataires officiels\n"
        "- Une analyse article par article, où chaque article est clairement identifié par son numéro ou identifiant, "
        "suivi d'une synthèse de son contenu et de ses implications juridiques, sans omission ni simplification excessive."
    )


def validate_text_summary(output: TaskOutput) -> Tuple[bool, str]:
    """
    Validate the output of the text summary task.

    Args:
        output: The output of the text summary task.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating whether the output is valid,
                         and a string containing the validated output or an error message.
    """
    text = output.raw

    # Check if the output contains all required sections
    required_sections = [
        "Titre officiel",
        "Date de publication",
        "Signataires officiels",
    ]
    missing_sections = [section for section in required_sections if section not in text]

    if missing_sections:
        return (
            False,
            f"Le résumé ne contient pas les sections suivantes: {', '.join(missing_sections)}",
        )

    # Check if the output is not too short
    if len(text.split()) < 50:
        return False, "Le résumé est trop court. Veuillez fournir plus de détails."

    return True, text


text_summary = Task(
    name="Résumé de texte juridique",
    description=get_task_description(),
    expected_output=get_expected_output(),
    agent=None,
    guardrail=validate_text_summary,
    max_retries=2,
    human_input=False,
)


def validate_image_payload(output: TaskOutput) -> Tuple[bool, TaskOutput]:
    """
    Validate the output of the image generation task.

    Args:
        output: The output of the image generation task.

    Returns:
        Tuple[bool, TaskOutput]: A tuple containing a boolean indicating whether the output is valid,
                               and the TaskOutput object or an error message.
    """
    if not output.pydantic:
        return False, "L'output n'est pas au format attendu (ImagePayload)"

    payload = output.pydantic

    # Check if image_url is not empty
    if not payload.image_url:
        return False, "L'URL de l'image est vide"

    # Check if image_description is not empty
    if not payload.image_description:
        return False, "La description de l'image est vide"

    return True, output


image_generation = Task(
    name="Génération d'image",
    description=(
        """
        Créez une image professionnelle et élégante représentant le texte juridique résumé ci-dessus.

        Style : Minimaliste, moderne, avec des couleurs douces
        Contexte : Juridique, législatif, officiel
        Public : Utilisateurs Instagram intéressés par l'actualité juridique
        Ne pas inclure : Texte, logos, drapeaux nationaux
        """
    ),
    expected_output=ImagePayload(image_url="", image_description="").model_dump_json(),
    context=[text_summary],
    agent=None,
    output_pydantic=ImagePayload,
    guardrail=validate_image_payload,
    max_retries=2,
)


def validate_caption(output: TaskOutput) -> Tuple[bool, str]:
    """
    Validate the output of the caption task.

    Args:
        output: The output of the caption task.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating whether the output is valid,
                         and a string containing the validated output or an error message.
    """
    text = output.raw

    # Check if the output is not too short
    if len(text.split()) < 20:
        return False, "La légende est trop courte. Veuillez fournir plus de détails."

    # Check if the output is not too long for Instagram (2200 characters limit)
    if len(text) > 2200:
        return (
            False,
            "La légende dépasse la limite de 2200 caractères d'Instagram. Veuillez la raccourcir.",
        )

    # Check for hashtags (should have at least 5)
    hashtags = [word for word in text.split() if word.startswith("#")]
    if len(hashtags) < 5:
        return (
            False,
            "La légende doit contenir au moins 5 hashtags pertinents. Veuillez en ajouter.",
        )

    # Check if there are too many hashtags (more than 30 is excessive)
    if len(hashtags) > 30:
        return (
            False,
            "La légende contient trop de hashtags. Limitez-vous à 30 maximum.",
        )

    # Check for emojis (should have at least one)
    # Simple emoji check - this is not comprehensive but catches common emoji patterns
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f700-\U0001f77f"  # alchemical symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027b0"  # Dingbats
        "\U000024c2-\U0001f251"
        "]+",
        flags=re.UNICODE,
    )

    if not emoji_pattern.search(text):
        return (
            False,
            "La légende doit contenir au moins un emoji pour améliorer l'engagement.",
        )

    # Check for formatting that's not allowed (asterisks and underscores for formatting)
    # Note: We now allow hashtags as they're required
    if "*" in text or "_" in text:
        return (
            False,
            "La légende contient des caractères de formatage (* _) qui ne sont pas autorisés.",
        )

    return True, text


caption = Task(
    name="Création de légende Instagram",
    description=(
        """
        Transformez l'analyse juridique détaillée en une publication Instagram claire et engageante. 

        Objectifs:
        - Rendre le contenu juridique accessible au grand public
        - Créer un texte concis et facile à comprendre
        - Structurer le contenu pour une lecture fluide sur mobile

        Contraintes Instagram:
        - Maximum 2200 caractères
        - Utilisez des paragraphes courts (2-3 lignes)
        - Incluez 5-10 hashtags pertinents à la fin
        - Évitez les formatages spéciaux (gras, italique, astérisques)
        - Incluez des émojis pertinents pour améliorer l'engagement

        Structure recommandée:
        1. Accroche captivante qui résume l'essentiel de la loi
        2. Présentation des points clés de manière simple
        3. Implications pratiques pour les citoyens
        4. Référence à la date de publication et aux signataires
        5. Hashtags pertinents
        """
    ),
    expected_output=(
        """
        Une légende Instagram prête à l'emploi qui:
        - Commence par une accroche captivante
        - Présente les points clés de la loi de manière simple et accessible
        - Explique les implications pratiques pour les citoyens
        - Utilise des émojis pertinents pour améliorer l'engagement
        - Inclut des paragraphes courts pour une lecture facile sur mobile
        - Se termine par 5-10 hashtags pertinents
        - Respecte la limite de 2200 caractères
        - Est formatée uniquement en texte brut (pas de formatage spécial)
        """
    ),
    context=[text_summary],
    agent=None,
    async_execution=False,
    guardrail=validate_caption,
    max_retries=2,
)
