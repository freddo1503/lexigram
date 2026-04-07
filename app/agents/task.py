"""
Task definitions for the Lexigram application.

This module defines the tasks used by the agents in the Lexigram application.
Each task is responsible for a specific part of the legal text processing pipeline:
- text_summary: Analyzes legal text and produces a structured summary
- image_generation: Creates a professional image based on the legal text
- caption: Converts legal analysis into an Instagram-friendly post
"""

from typing import Any, Tuple, cast

from crewai import Task
from crewai.lite_agent import LiteAgentOutput
from crewai.tasks.task_output import TaskOutput

from app.config import agents_config, settings
from app.models.lex_pictor import ImagePayload
from app.text_utils import EMOJI_PATTERN

task_config = agents_config["tasks"]["text_summary"]
image_task_config = agents_config["tasks"]["image_generation"]
caption_task_config = agents_config["tasks"]["caption"]


def validate_text_summary(output: TaskOutput | LiteAgentOutput) -> Tuple[bool, str]:
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
    description=agents_config["tasks"]["text_summary"]["description"],
    expected_output=agents_config["tasks"]["text_summary"]["expected_output"],
    agent=None,
    guardrail=validate_text_summary,
    guardrail_max_retries=3,
    human_input=False,
)


def validate_image_payload(
    output: TaskOutput | LiteAgentOutput,
) -> Tuple[bool, Any]:
    if not output.pydantic:
        return False, "L'output n'est pas au format attendu (ImagePayload)"
    payload = cast(ImagePayload, output.pydantic)
    if not payload.image_url:
        return False, "L'URL de l'image est vide"
    if not payload.image_description:
        return False, "La description de l'image est vide"
    # Reject hallucinated URLs — must come from our S3 bucket
    bucket = settings.s3_bucket_name or ""
    if bucket and bucket not in payload.image_url:
        return False, (
            f"L'URL de l'image ne provient pas du bucket S3 configuré ({bucket}). "
            "Utilisez l'outil Mistral Image Tool pour générer l'image."
        )
    return True, output


image_generation = Task(
    name=image_task_config["name"],
    description=image_task_config["description"],
    expected_output=ImagePayload(image_url="", image_description="").model_dump_json(),
    context=[text_summary],
    agent=None,
    output_pydantic=ImagePayload,
    guardrail=validate_image_payload,
    guardrail_max_retries=3,
)


def validate_caption(output: TaskOutput | LiteAgentOutput) -> Tuple[bool, str]:
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
    if not EMOJI_PATTERN.search(text):
        return (
            False,
            "La légende doit contenir au moins un emoji pour améliorer l'engagement.",
        )

    # Strip markdown formatting characters — LLMs produce these despite instructions,
    # and Instagram renders plain text only.
    text = text.replace("*", "").replace("_", "")

    return True, text


caption = Task(
    name=caption_task_config["name"],
    description=caption_task_config["description"],
    expected_output=caption_task_config["expected_output"],
    context=[text_summary],
    agent=None,
    async_execution=False,
    guardrail=validate_caption,
    guardrail_max_retries=3,
)
