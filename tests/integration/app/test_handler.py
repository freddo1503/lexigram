import json

from app.config import AWS_SECRET_NAME


def test_secrets_manager_connectivity(secrets_manager_client):
    """Verify AWS Secrets Manager returns a non-empty secret."""
    response = secrets_manager_client.get_secret_value(SecretId=AWS_SECRET_NAME)
    secrets = json.loads(response["SecretString"])

    assert isinstance(secrets, dict), "Expected secret to be a dictionary."
    assert secrets, (
        "The secret dictionary is empty. "
        "Ensure that the secret exists in AWS Secrets Manager."
    )


def test_settings_loads_secrets():
    """Verify that LexigramSettings picks up values from env/secrets sources."""
    from app.config import LexigramSettings

    s = LexigramSettings()
    assert isinstance(s.log_level, str)

    # At least one secret-sourced field should be populated
    secret_fields = [
        s.legifrance_client_id,
        s.legifrance_client_secret,
        s.mistral_api_key,
        s.instagram_access_token,
    ]
    loaded = [f for f in secret_fields if f is not None]
    assert loaded, "No secrets loaded from any source (env, .env, or Secrets Manager)."
