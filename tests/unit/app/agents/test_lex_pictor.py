from unittest.mock import MagicMock, patch

import pytest

# Mock boto3 before importing any modules that use it
with patch("boto3.client"):
    from app.agents.lex_pictor import DallETool, LexPictor
    from app.models.lex_pictor import ImagePayload


class MockImageData:
    def __init__(self, url, revised_prompt):
        self.url = url
        self.revised_prompt = revised_prompt


class MockImageResponse:
    def __init__(self, data):
        self.data = data


@pytest.fixture
def mock_openai_client():
    with patch("app.agents.lex_pictor.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        yield mock_client


def test_dalle_tool_run_success(mock_openai_client):
    mock_image_data = MockImageData(
        url="https://example.com/image.jpg",
        revised_prompt="A beautiful landscape with mountains",
    )
    mock_response = MockImageResponse(data=[mock_image_data])
    mock_openai_client.images.generate.return_value = mock_response

    tool = DallETool()
    result = tool._run(image_description="A landscape")

    assert result, "The result should not be empty"

    # Verify the result is an ImagePayload object
    assert isinstance(result, ImagePayload), (
        "The result should be an ImagePayload object"
    )

    # Validate the ImagePayload properties
    assert result.image_url == "https://example.com/image.jpg", (
        "The image_url should match the mock data"
    )
    assert result.image_description == "A beautiful landscape with mountains", (
        "The image_description should match the mock data"
    )

    mock_openai_client.images.generate.assert_called_once_with(
        model="dall-e-3",
        prompt="A landscape",
        size="1024x1024",
        n=1,
    )


def test_dalle_tool_run_missing_description():
    tool = DallETool()
    result = tool._run()

    assert result == "Image description is required."


@patch("app.agents.lex_pictor.agents_config")
@patch("app.agents.lex_pictor.settings")
@patch("app.agents.lex_pictor.LLM")
def test_lex_pictor_initialization(mock_llm, mock_settings, mock_agents_config):
    mock_settings.openai_api_key = "test_api_key"
    mock_llm_instance = MagicMock()
    mock_llm.return_value = mock_llm_instance

    # Set up the mock for agents_config with proper string values
    mock_agents_config.__getitem__.return_value = {
        "lex_pictor": {
            "role": "Artiste Visuel Innovant",
            "goal": "Créer des oeuvres d'art visuelles captivantes et originales en utilisant des techniques numériques avancées",
            "backstory": "LexPictor est un artiste visuel passionné, spécialisé dans l'intégration de technologies numériques",
        }
    }

    agent = LexPictor()

    assert agent.role == "Artiste Visuel Innovant"
    assert "Créer des oeuvres d'art visuelles captivantes" in agent.goal
    assert "LexPictor est un artiste visuel passionné" in agent.backstory
    assert len(agent.tools) == 1
    assert isinstance(agent.tools[0], DallETool)
    assert agent.allow_delegation is False
    assert agent.verbose is True

    mock_llm.assert_called_once_with(model="gpt-4", api_key="test_api_key")


@patch("app.agents.lex_pictor.OpenAI")
def test_dalle_tool_run_api_error(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.images.generate.side_effect = Exception("API Error")

    tool = DallETool()

    with pytest.raises(Exception, match="API Error"):
        tool._run(image_description="A landscape")
