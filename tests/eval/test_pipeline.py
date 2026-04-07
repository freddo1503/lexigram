"""End-to-end evaluation tests for the Lexigram pipeline.

Programmatic checks validate hard constraints (format, length, structure).
LLM-as-judge tests use Claude Opus to evaluate soft criteria (quality, clarity).
"""

from app.text_utils import EMOJI_PATTERN
from tests.eval.scoring import score_programmatic, score_with_claude_judge

# ---------------------------------------------------------------------------
# Programmatic checks
# ---------------------------------------------------------------------------


def test_text_summary_sections(text_summary_output, langfuse_client, trace_id):
    """Verify text summary contains required sections."""
    text = text_summary_output.raw
    required_sections = [
        "Titre officiel",
        "Date de publication",
        "Signataires officiels",
    ]
    missing = [s for s in required_sections if s not in text]
    passed = len(missing) == 0

    score_programmatic(
        langfuse_client,
        trace_id,
        "text_summary_sections",
        passed,
        f"Missing: {', '.join(missing)}" if missing else "All sections present",
    )
    assert passed, f"Missing required sections: {', '.join(missing)}"


def test_text_summary_min_words(text_summary_output, langfuse_client, trace_id):
    """Verify text summary has sufficient length."""
    text = text_summary_output.raw
    word_count = len(text.split())
    passed = word_count >= 50

    score_programmatic(
        langfuse_client,
        trace_id,
        "text_summary_word_count",
        passed,
        f"Word count: {word_count}",
    )
    assert passed, f"Text summary too short: {word_count} words (min 50)"


def test_image_valid(image_generation_output, langfuse_client, trace_id):
    """Verify image generation produced a valid result stored in S3."""
    payload = image_generation_output.pydantic
    url_valid = bool(
        payload and payload.image_url and "lexigram-images" in payload.image_url
    )
    desc_valid = bool(payload and payload.image_description)
    passed = url_valid and desc_valid

    score_programmatic(
        langfuse_client,
        trace_id,
        "image_valid",
        passed,
        f"url_valid={url_valid}, desc_valid={desc_valid}, url={getattr(payload, 'image_url', 'N/A')[:100]}",
    )
    assert passed, (
        f"Image validation failed: url_valid={url_valid}, desc_valid={desc_valid}, "
        f"url={getattr(payload, 'image_url', 'N/A')[:100]}"
    )


def test_caption_char_limit(caption_output, langfuse_client, trace_id):
    """Verify caption respects Instagram character limit."""
    text = caption_output.raw
    passed = len(text) <= 2200

    score_programmatic(
        langfuse_client,
        trace_id,
        "caption_char_limit",
        passed,
        f"Length: {len(text)} chars",
    )
    assert passed, f"Caption too long: {len(text)} chars (max 2200)"


def test_caption_min_words(caption_output, langfuse_client, trace_id):
    """Verify caption has sufficient length."""
    text = caption_output.raw
    word_count = len(text.split())
    passed = word_count >= 20

    score_programmatic(
        langfuse_client,
        trace_id,
        "caption_word_count",
        passed,
        f"Word count: {word_count}",
    )
    assert passed, f"Caption too short: {word_count} words (min 20)"


def test_caption_hashtags(caption_output, langfuse_client, trace_id):
    """Verify caption contains appropriate number of hashtags."""
    text = caption_output.raw
    hashtags = [w for w in text.split() if w.startswith("#")]
    count = len(hashtags)
    passed = 5 <= count <= 30

    score_programmatic(
        langfuse_client,
        trace_id,
        "caption_hashtags",
        passed,
        f"Hashtag count: {count}",
    )
    assert passed, f"Hashtag count out of range: {count} (expected 5-30)"


def test_caption_emojis(caption_output, langfuse_client, trace_id):
    """Verify caption contains at least one emoji."""
    text = caption_output.raw
    passed = bool(EMOJI_PATTERN.search(text))

    score_programmatic(
        langfuse_client,
        trace_id,
        "caption_emojis",
        passed,
        "Emoji found" if passed else "No emoji found",
    )
    assert passed, "Caption must contain at least one emoji"


def test_caption_no_formatting(caption_output, langfuse_client, trace_id):
    """Verify caption doesn't contain markdown formatting characters."""
    text = caption_output.raw
    has_asterisks = "*" in text
    has_underscores = "_" in text
    passed = not has_asterisks and not has_underscores

    score_programmatic(
        langfuse_client,
        trace_id,
        "caption_no_formatting",
        passed,
        f"asterisks={has_asterisks}, underscores={has_underscores}",
    )
    assert passed, "Caption contains formatting characters (* or _)"


# ---------------------------------------------------------------------------
# LLM-as-judge (Claude Opus)
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluator for a French legal content summarization system.
Rate the content on the given criteria using a scale of 1-5.
Respond ONLY with a JSON object containing scores and a brief comment.
Format: {"overall": <1-5>, "criteria": {"<name>": <1-5>, ...}, "comment": "<brief explanation>"}
"""


def test_text_summary_quality(
    text_summary_output, anthropic_client, langfuse_client, trace_id
):
    """Judge text summary quality with Claude Opus."""
    text = text_summary_output.raw
    scores = score_with_claude_judge(
        anthropic_client,
        langfuse_client,
        trace_id,
        "text_summary_quality",
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_prompt=f"""\
Evaluate this French legal text summary on:
1. accuracy — does it faithfully represent legal content?
2. accessibility — is it understandable by a non-lawyer French citizen?
3. citizen_friendliness — does it explain the impact on people's daily lives?

Summary:
{text}
""",
    )
    overall = scores.get("overall", 0)
    assert overall >= 3, (
        f"Text summary quality too low: {overall}/5 — {scores.get('comment', '')}"
    )


def test_caption_quality(
    caption_output, text_summary_output, anthropic_client, langfuse_client, trace_id
):
    """Judge caption quality with Claude Opus."""
    caption = caption_output.raw
    summary = text_summary_output.raw
    scores = score_with_claude_judge(
        anthropic_client,
        langfuse_client,
        trace_id,
        "caption_quality",
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_prompt=f"""\
Evaluate this Instagram caption for a French legal content account.
The caption was generated from the legal summary below.

Criteria:
1. clarity — is the message clear and easy to understand?
2. engagement — would a French citizen find this interesting on Instagram?
3. accuracy — does the caption accurately represent the law summarized below?

Caption:
{caption}

Original summary:
{summary}
""",
    )
    overall = scores.get("overall", 0)
    assert overall >= 3, (
        f"Caption quality too low: {overall}/5 — {scores.get('comment', '')}"
    )


def test_image_description_quality(
    image_generation_output,
    text_summary_output,
    anthropic_client,
    langfuse_client,
    trace_id,
):
    """Judge image description quality with Claude Opus."""
    payload = image_generation_output.pydantic
    description = payload.image_description if payload else ""
    summary = text_summary_output.raw
    scores = score_with_claude_judge(
        anthropic_client,
        langfuse_client,
        trace_id,
        "image_description_quality",
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_prompt=f"""\
Evaluate this image description generated for a French legal content Instagram post.
The image should visually evoke the legal concepts without containing text or logos.

Criteria:
1. relevance — does the description relate to the legal content summarized below?
2. visual_quality — would this description produce an appropriate, professional image?

Image description:
{description}

Original legal summary:
{summary}
""",
    )
    overall = scores.get("overall", 0)
    assert overall >= 3, (
        f"Image description quality too low: {overall}/5 — {scores.get('comment', '')}"
    )
