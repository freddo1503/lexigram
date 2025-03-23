import json

import pytest
from agents.lex_pictor import DallETool


def test_dalle_tool_success():
    tool = DallETool()

    # Define a valid image description
    valid_input = {"image_description": "A futuristic cityscape at sunset"}

    # Run the tool
    result = tool._run(**valid_input)
    assert result, "The result should not be empty."

    # Parse the returned JSON
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        pytest.fail("The result is not a valid JSON object.")

    # Validate the JSON structure
    assert "image_url" in data, "The result should contain an image_url."
    assert "image_description" in data, (
        "The result should contain an image_description."
    )

    print("Image URL:", data["image_url"])
