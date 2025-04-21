"""
Task definitions for the Lexigram application.

This module defines the tasks used by the agents in the Lexigram application.
Each task is responsible for a specific part of the legal text processing pipeline:
- text_summary: Analyzes legal text and produces a structured summary
- image_generation: Creates a professional image based on the legal text
- caption: Converts legal analysis into an Instagram-friendly post
"""

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
        "4. Synthèse détaillée des principaux points sans altération du contenu : {contenu}"
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
        "- Une synthèse détaillée des principaux points, sans omission ni simplification excessive."
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
        return False, "The caption is too short. Please provide more details."

    # Check if the output is not too long for Instagram
    if len(text.split()) > 300:
        return (
            False,
            "The caption is too long for Instagram. Please make it more concise.",
        )

    # Check for formatting that's not allowed
    if "*" in text or "_" in text or "#" in text:
        return (
            False,
            "The caption contains formatting characters (* _ #) that are not allowed.",
        )

    return True, text


caption = Task(
    name="Création de légende Instagram",
    description=(
        "Convert a detailed legal analysis into a clear and engaging Instagram post. "
        "Ensure the content is concise, easy to understand, and structured for readability. "
        "Do not use bold, italics, asterisks, or any special formatting—just plain text. "
        "The link to the original text will be included in the comment."
    ),
    expected_output=(
        "An Instagram-ready text with key takeaways, bullet points, or a carousel-friendly breakdown. "
        "The content should be legally accurate, engaging, and accessible to a broad audience, formatted strictly in plain text."
    ),
    context=[text_summary],
    agent=None,
    async_execution=False,
    guardrail=validate_caption,
    max_retries=2,
)
