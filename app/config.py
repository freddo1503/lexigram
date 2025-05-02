import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import boto3
import dotenv
import yaml

from app.api_client import LegifranceApiClient

dotenv.load_dotenv()

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp")

# Setup logging
logger = logging.getLogger(__name__)
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger.setLevel(log_level)

_secrets_cache: Dict[str, Dict[str, str]] = {}


def get_all_secrets(
    client: boto3.client = None, secret_name: str = "my-env-secrets"
) -> Dict[str, str]:
    """
    Retrieve all environment variables from AWS Secrets Manager and cache them.
    """
    if secret_name in _secrets_cache:
        return _secrets_cache[secret_name]

    if client is None:
        client = boto3.client("secretsmanager")

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        _secrets_cache[secret_name] = secret
        logger.debug(f"Secrets loaded and cached for '{secret_name}'.")
        return secret
    except Exception as e:
        logger.error(f"Error retrieving secret '{secret_name}': {e}")
        return {}


_secrets = get_all_secrets()


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable from secrets, then system environment, with a fallback to default.
    """
    return _secrets.get(key) or os.getenv(key, default)


LEGIFRANCE_CLIENT_ID = get_env_var("LEGIFRANCE_CLIENT_ID")
LEGIFRANCE_CLIENT_SECRET = get_env_var("LEGIFRANCE_CLIENT_SECRET")
LEGIFRANCE_TOKEN_URL = get_env_var(
    "LEGIFRANCE_TOKEN_URL", "https://sandbox-oauth.gouv.fr/api/oauth/token"
)
LEGIFRANCE_API_URL = get_env_var(
    "LEGIFRANCE_API_URL", "https://sandbox-api.gouv.fr/dila/legifrance/lf-engine-app"
)
OPENAI_API_KEY = get_env_var("OPENAI_API_KEY")
MISTRAL_API_KEY = get_env_var("MISTRAL_API_KEY")
ACCESS_TOKEN = get_env_var("ACCESS_TOKEN")
DYNAMO_TABLE_NAME = get_env_var("DYNAMO_TABLE_NAME")

api_client = LegifranceApiClient(
    base_url=LEGIFRANCE_API_URL,
    client_id=LEGIFRANCE_CLIENT_ID,
    client_secret=LEGIFRANCE_CLIENT_SECRET,
    token_url=LEGIFRANCE_TOKEN_URL,
)

AGENTS_CONFIG_PATH = Path(__file__).parent / "config" / "agents.yml"


def load_agents_config() -> dict[str, dict]:
    """
    Load the agents and tasks configuration from the YAML file.

    Returns:
        dict: The configuration dictionary with agents and tasks.
    """
    try:
        with open(AGENTS_CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        logger.debug(f"Agents configuration loaded from {AGENTS_CONFIG_PATH}")
        return config
    except Exception as e:
        logger.error(
            f"Error loading agents configuration from {AGENTS_CONFIG_PATH}: {e}"
        )
        return {"agents": {}, "tasks": {}}


agents_config = load_agents_config()
