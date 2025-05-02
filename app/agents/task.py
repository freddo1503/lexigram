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

from app import config
from app.models.lex_pictor import ImagePayload

task_config = config.agents_config["tasks"]["text_summary"]
image_task_config = config.agents_config["tasks"]["image_generation"]
caption_task_config = config.agents_config["tasks"]["caption"]


def validate_text_summary(output: TaskOutput) -> Tuple[bool, str]:
    text = output.raw
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
    if len(text.split()) < 50:
        return False, "Le résumé est trop court. Veuillez fournir plus de détails."
    return True, text


text_summary = Task(
    name=task_config["name"],
    description=config.agents_config["tasks"]["text_summary"]["description"],
    expected_output=config.agents_config["tasks"]["text_summary"]["expected_output"],
    agent=None,
    guardrail=validate_text_summary,
    max_retries=2,
    human_input=False,
)


def validate_image_payload(output: TaskOutput) -> Tuple[bool, TaskOutput]:
    if not output.pydantic:
        return False, "L'output n'est pas au format attendu (ImagePayload)"
    payload = output.pydantic
    if not payload.image_url:
        return False, "L'URL de l'image est vide"
    if not payload.image_description:
        return False, "La description de l'image est vide"
    return True, output


image_generation = Task(
    name=image_task_config["name"],
    description=image_task_config["description"],
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
    name=caption_task_config["name"],
    description=caption_task_config["description"],
    expected_output=caption_task_config["expected_output"],
    context=[text_summary],
    agent=None,
    async_execution=False,
    guardrail=validate_caption,
    max_retries=2,
)
