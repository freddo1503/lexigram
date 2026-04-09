from unittest.mock import MagicMock, patch

import pytest

# Mock boto3 before importing any modules that use it
with patch("boto3.client"):
    from app.agents.lex_pictor import LexPictor, MistralImageTool
    from app.models.lex_pictor import ImagePayload


@pytest.fixture
def mock_mistral_client():
    with patch("app.agents.lex_pictor.Mistral") as mock_mistral:
        mock_client = MagicMock()
        mock_mistral.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_s3_client():
    with patch("app.agents.lex_pictor.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        yield mock_s3


def test_mistral_image_tool_run_success(mock_mistral_client, mock_s3_client):
    # Mock agent creation
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"
    mock_mistral_client.beta.agents.create.return_value = mock_agent

    # Mock conversation response — file_id is nested in content chunks
    # See: https://docs.mistral.ai/agents/tools/built-in/image_generation
    mock_chunk = MagicMock()
    mock_chunk.file_id = "file-456"
    mock_output = MagicMock()
    mock_output.content = [mock_chunk]
    mock_response = MagicMock()
    mock_response.outputs = [mock_output]
    mock_mistral_client.beta.conversations.start.return_value = mock_response

    # Mock file download
    mock_file = MagicMock()
    mock_file.read.return_value = b"fake-png-data"
    mock_mistral_client.files.download.return_value = mock_file

    tool = MistralImageTool()
    with (
        patch("app.agents.lex_pictor.settings") as mock_settings,
        patch("app.models.lex_pictor.settings") as mock_model_settings,
        patch("app.agents.lex_pictor.Image") as mock_image,
    ):
        mock_settings.mistral_api_key = "test-key"
        mock_settings.s3_bucket_name = "test-bucket"
        mock_settings.mistral_image_model = "mistral-medium-latest"
        mock_settings.aws_region = "eu-west-3"
        mock_model_settings.s3_bucket_name = "test-bucket"
        mock_model_settings.aws_region = "eu-west-3"
        # Mock PIL Image.open().convert().save() chain
        mock_img = MagicMock()
        mock_image.open.return_value.convert.return_value = mock_img
        mock_img.save.side_effect = lambda buf, fmt, **kw: buf.write(b"fake-jpeg-data")
        result = tool._run(image_description="A legal scene")

        assert isinstance(result, str)
        payload = ImagePayload.model_validate_json(result)
        assert "test-bucket" in payload.image_url
        assert payload.image_url.endswith(".jpg")
        assert payload.image_description == "A legal scene"

    mock_s3_client.put_object.assert_called_once()
    call_kwargs = mock_s3_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "test-bucket"
    assert call_kwargs["ContentType"] == "image/jpeg"


@patch("app.agents.lex_pictor.Mistral")
def test_mistral_image_tool_run_missing_description(mock_mistral):
    mock_mistral.return_value = MagicMock()
    tool = MistralImageTool()
    result = tool._run()

    assert result == "Image description is required."


@patch("app.agents.lex_pictor.agents_config")
@patch("app.agents.lex_pictor.settings")
def test_lex_pictor_initialization(mock_settings, mock_agents_config):
    mock_settings.mistral_api_key = "test_api_key"
    mock_settings.default_llm_model = "mistral/mistral-large-latest"

    mock_agents_config.__getitem__.return_value = {
        "lex_pictor": {
            "role": "Directeur Artistique Numérique",
            "goal": "Créer des images minimalistes et évocatrices",
            "backstory": "Vous êtes spécialisé dans la création d'images conceptuelles",
        }
    }

    agent = LexPictor()

    assert agent.role == "Directeur Artistique Numérique"
    assert "images minimalistes" in agent.goal
    assert "images conceptuelles" in agent.backstory
    assert agent.tools is not None
    assert len(agent.tools) == 1
    assert isinstance(agent.tools[0], MistralImageTool)
    assert agent.allow_delegation is False
    assert agent.verbose is True


@patch("app.agents.lex_pictor.Mistral")
def test_mistral_image_tool_run_api_error(mock_mistral):
    mock_client = MagicMock()
    mock_mistral.return_value = mock_client
    mock_client.beta.agents.create.side_effect = Exception("API Error")

    tool = MistralImageTool()
    with patch("app.agents.lex_pictor.settings") as mock_settings:
        mock_settings.mistral_api_key = "test-key"
        with pytest.raises(Exception, match="API Error"):
            tool._run(image_description="A legal scene")


def test_mistral_image_tool_run_no_file_id(mock_mistral_client):
    # Mock agent creation
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"
    mock_mistral_client.beta.agents.create.return_value = mock_agent

    # Mock response with no file_id in content chunks
    mock_chunk = MagicMock(spec=[])  # empty spec = no file_id attribute
    mock_output = MagicMock()
    mock_output.content = [mock_chunk]
    mock_response = MagicMock()
    mock_response.outputs = [mock_output]
    mock_mistral_client.beta.conversations.start.return_value = mock_response

    tool = MistralImageTool()
    with patch("app.agents.lex_pictor.settings") as mock_settings:
        mock_settings.mistral_api_key = "test-key"
        result = tool._run(image_description="A legal scene")

    assert result == "Image generation returned no file."
