import os

from app.config import get_all_secrets


def test_get_all_secrets_integration(secrets_manager_client):
    secret_name = "my-env-secrets"

    secret = get_all_secrets(client=secrets_manager_client, secret_name=secret_name)

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

    cached_secret = get_all_secrets(
        client=secrets_manager_client, secret_name=secret_name
    )
    assert cached_secret is secret, "Secrets caching not working as expected."

    print(
        "Integration test passed: Secrets and environment variables are set correctly."
    )
