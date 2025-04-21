from app.agents.lex_pictor import DallETool
from app.models.lex_pictor import ImagePayload


def test_dalle_tool_success():
    tool = DallETool()

    # Define a valid image description
    valid_input = {"image_description": "A futuristic cityscape at sunset"}

    # Run the tool
    result = tool._run(**valid_input)
    assert result, "The result should not be empty."

    # Verify the result is an ImagePayload object
    assert isinstance(result, ImagePayload), (
        "The result should be an ImagePayload object."
    )

    # Validate the ImagePayload properties
    assert result.image_url, "The result should contain a non-empty image_url."
    assert result.image_description, (
        "The result should contain a non-empty image_description."
    )
