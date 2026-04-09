import boto3
import pytest
from botocore.exceptions import ClientError
from mistralai.models.sdkerror import SDKError

from app.agents.lex_pictor import MistralImageTool
from app.config import settings
from app.models.lex_pictor import ImagePayload


def _s3_bucket_exists() -> bool:
    """Check if the configured S3 bucket exists and is accessible."""
    if not settings.s3_bucket_name:
        return False
    try:
        boto3.client("s3").head_bucket(Bucket=settings.s3_bucket_name)
        return True
    except (ClientError, Exception):
        return False


@pytest.mark.skipif(
    not settings.mistral_api_key or not _s3_bucket_exists(),
    reason="Requires MISTRAL_API_KEY and live S3 bucket",
)
def test_mistral_image_tool_success():
    tool = MistralImageTool()

    # Define a valid image description
    valid_input = {"image_description": "A futuristic cityscape at sunset"}

    # Run the tool — returns JSON string
    try:
        result = tool._run(**valid_input)
    except SDKError as e:
        if "429" in str(e) or "rate limit" in str(e).lower():
            pytest.skip(f"Mistral image API rate limited: {e}")
        raise
    assert result, "The result should not be empty."

    # Parse and validate the ImagePayload
    payload = ImagePayload.model_validate_json(result)
    assert payload.image_url, "The result should contain a non-empty image_url."
    assert payload.image_url.startswith("https://"), (
        "The image_url should be an S3 URL."
    )
    assert payload.image_description, (
        "The result should contain a non-empty image_description."
    )
