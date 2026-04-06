"""Scoring utilities for Langfuse evaluation."""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)


def score_programmatic(
    langfuse_client, trace_id: str, name: str, passed: bool, comment: str = ""
):
    """Submit a programmatic boolean score to Langfuse."""
    langfuse_client.score(
        trace_id=trace_id,
        name=name,
        value=1.0 if passed else 0.0,
        comment=comment,
    )


def score_with_claude_judge(
    anthropic_client: anthropic.Anthropic,
    langfuse_client,
    trace_id: str,
    criterion_name: str,
    system_prompt: str,
    user_prompt: str,
) -> dict:
    """Send a judging prompt to Claude Opus and submit scores to Langfuse.

    Returns the parsed scores dict from the judge response.
    """
    response = anthropic_client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = response.content[0].text  # ty: ignore[unresolved-attribute]

    try:
        scores = json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse judge response as JSON: %s", response_text[:200]
        )
        scores = {"overall": 3, "comment": response_text[:500]}

    overall = scores.get("overall", 3)
    comment = scores.get("comment", "")

    langfuse_client.score(
        trace_id=trace_id,
        name=criterion_name,
        value=float(overall) / 5.0,
        comment=str(comment)[:500],
    )

    return scores
