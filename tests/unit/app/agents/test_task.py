"""Unit tests for caption guardrail rules in app.agents.task."""

from types import SimpleNamespace
from typing import cast

import pytest
from crewai.tasks.task_output import TaskOutput

from app.agents.task import validate_caption


def _output(text: str) -> TaskOutput:
    """Build a fake TaskOutput exposing only the `raw` attribute used by the guardrail."""
    return cast(TaskOutput, SimpleNamespace(raw=text))


VALID_CAPTION = """Le Sénat adopte une réforme majeure du droit du travail pour 2027

📜 Le texte modifie les conditions de rupture conventionnelle et encadre le télétravail.

Ce qui change :
✅ Indemnité minimale revalorisée
✅ Délai de rétractation allongé
✅ Télétravail opposable sous conditions

👥 Pour vous, concrètement : les salariés disposeront de nouveaux droits si le décret est publié.

📅 Publié le 9 avril 2026

#droit #travail #reforme #senat #legifrance #france #actualite"""


def test_validate_caption_accepts_target_template():
    ok, result = validate_caption(_output(VALID_CAPTION))
    assert ok is True, f"Target template rejected: {result}"
    assert "*" not in result and "_" not in result


def test_validate_caption_rejects_emoji_in_hook():
    bad = (
        "📜 Le Sénat adopte une réforme majeure du droit du travail\n\n"
        + "\n\n".join(VALID_CAPTION.split("\n\n")[1:])
    )
    ok, msg = validate_caption(_output(bad))
    assert ok is False
    assert "accroche" in msg.lower()


def test_validate_caption_rejects_long_hook():
    long_hook = "A" * 160
    bad = long_hook + "\n\n" + "\n\n".join(VALID_CAPTION.split("\n\n")[1:])
    ok, msg = validate_caption(_output(bad))
    assert ok is False
    assert "150" in msg


def test_validate_caption_rejects_missing_paragraph_breaks():
    flat = VALID_CAPTION.replace("\n\n", " ")
    ok, msg = validate_caption(_output(flat))
    assert ok is False
    assert "section" in msg.lower() or "ligne" in msg.lower()


def test_validate_caption_rejects_emoji_ceiling():
    # 9 distinct emoji characters in the body — over the cap of 8.
    over = (
        "Le Sénat adopte une réforme majeure\n\n"
        "📜 Contexte rapide avec 📢 📌 🔍 ⚖️ ✨ 🎯 🚀 🌟 en trop.\n\n"
        "Ce qui change :\n✅ Point un\n✅ Point deux\n\n"
        "👥 Pour vous\n\n"
        "📅 Publié le 9 avril 2026\n\n"
        "#droit #travail #reforme #senat #legifrance"
    )
    ok, msg = validate_caption(_output(over))
    assert ok is False
    assert "emoji" in msg.lower()


def test_validate_caption_rejects_too_few_hashtags():
    few = VALID_CAPTION.rsplit("\n\n", 1)[0] + "\n\n#droit #travail"
    ok, msg = validate_caption(_output(few))
    assert ok is False
    assert "hashtag" in msg.lower()


@pytest.mark.parametrize(
    "markdown_char",
    ["*", "_"],
)
def test_validate_caption_strips_markdown(markdown_char):
    dirty = VALID_CAPTION.replace("réforme", f"{markdown_char}réforme{markdown_char}")
    ok, result = validate_caption(_output(dirty))
    assert ok is True
    assert markdown_char not in result
