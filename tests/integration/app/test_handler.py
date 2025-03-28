# test_integration_secrets.py
import os

from app.config import get_all_secrets  # adjust import if needed


def test_get_all_secrets_integration():
    secret_name = "my-env-secrets"

    # Call the function to retrieve secrets from AWS Secrets Manager
    secret = get_all_secrets(secret_name)

    # The secret should be a non-empty dictionary if retrieval was successful.
    # Depending on your secret's content, you can adjust these assertions.
    assert isinstance(secret, dict), "Expected secret to be a dictionary."
    assert secret, (
        "The secret dictionary returned is empty. Ensure that the secret exists in AWS Secrets Manager."
    )

    for key, value in secret.items():
        env_val = os.environ.get(key)
        assert env_val is not None, f"Environment variable '{key}' was not set."
        assert env_val == str(value), (
            f"Environment variable '{key}' has value '{env_val}', expected '{value}'."
        )

    cached_secret = get_all_secrets(secret_name)
    assert cached_secret is secret, "Secrets caching not working as expected."

    print(
        "Integration test passed: Secrets and environment variables are set correctly."
    )
