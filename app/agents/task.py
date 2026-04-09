"""
Task definitions for the Lexigram application.

This module defines the tasks used by the agents in the Lexigram application.
Each task is responsible for a specific part of the legal text processing pipeline:
- text_summary: Analyzes legal text and produces a structured summary
- image_generation: Creates a professional image based on the legal text
- caption: Converts legal analysis into an Instagram-friendly post
"""

from typing import Any, Tuple

from crewai import Task
from crewai.lite_agent import LiteAgentOutput
from crewai.tasks.task_output import TaskOutput
from pydantic import ValidationError

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


def _s3_image_exists(image_url: str) -> bool:
    """Check if an image actually exists at the given S3 URL."""
    import boto3
    from botocore.exceptions import ClientError

    bucket = settings.s3_bucket_name
    if not bucket or bucket not in image_url:
        return False
    # Extract S3 key from URL: https://<bucket>.s3.<region>.amazonaws.com/<key>
    try:
        key = image_url.split(".amazonaws.com/", 1)[1]
        boto3.client("s3").head_object(Bucket=bucket, Key=key)
        return True
    except (ClientError, IndexError):
        return False


def validate_image_payload(
    output: TaskOutput | LiteAgentOutput,
) -> Tuple[bool, Any]:
    # With result_as_answer=True on MistralImageTool, the task's raw output
    # is the tool's JSON return value. Parse it directly.
    try:
        payload = ImagePayload.model_validate_json(output.raw)
    except ValidationError as e:
        return False, (
            f"L'output n'est pas un ImagePayload valide ({e}). "
            "Vous DEVEZ appeler l'outil 'Mistral Image Tool' avec une description, "
            "et retourner SON RÉSULTAT tel quel (sans le modifier)."
        )
    if not _s3_image_exists(payload.image_url):
        return False, (
            "L'image n'existe pas dans S3 — l'URL a été inventée. "
            "Vous DEVEZ appeler l'outil 'Mistral Image Tool' avec une description "
            "et retourner son résultat sans modification."
        )
    return True, payload


image_generation = Task(
    name=image_task_config["name"],
    description=image_task_config["description"],
    expected_output='{"image_url": "https://<bucket>.s3.<region>.amazonaws.com/images/<uuid>.jpg", "image_description": "<description>"}',
    context=[text_summary],
    agent=None,
    guardrail=validate_image_payload,
    guardrail_max_retries=1,
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

    # First line (hook) must be plain text and survive mobile truncation (~125 chars).
    # We allow up to 150 to leave headroom for French words.
    first_line = text.split("\n", 1)[0].strip()
    if EMOJI_PATTERN.search(first_line):
        return (
            False,
            "La première ligne (accroche) ne doit contenir aucun emoji. Réservez les émojis aux marqueurs de section.",
        )
    if len(first_line) > 150:
        return (
            False,
            "La première ligne (accroche) dépasse 150 caractères. Elle doit fonctionner seule avant la troncature « ... plus ».",
        )

    # Enforce section separation via blank lines. The target template has
    # 5 section breaks + 1 blank line before the hashtag block = 6 blank lines;
    # 4 is a safe floor that tolerates minor drift.
    if text.count("\n\n") < 4:
        return (
            False,
            "La légende doit être structurée en sections séparées par des lignes vides (double saut de ligne).",
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

    # Soft ceiling on emojis: 3-6 is optimal, 8 is the hard max to discourage spam.
    emoji_count = sum(len(match) for match in EMOJI_PATTERN.findall(text))
    if emoji_count > 8:
        return (
            False,
            "La légende contient trop d'emojis. Limitez-vous à 8 maximum (3 à 6 recommandé).",
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
