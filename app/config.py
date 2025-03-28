import json
import logging
import os
from typing import Dict

import boto3
import dotenv

from app.api_client import LegifranceApiClient

# Load .env file
dotenv.load_dotenv()

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_STORAGE_DIR"] = "/tmp"


logger = logging.getLogger(__name__)
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger.setLevel(log_level)

# Cache for secrets
secrets_cache = {}

region_name = "eu-west-3"
client = boto3.client("secretsmanager", region_name=region_name)


def get_all_secrets(secret_name: str = "my-env-secrets") -> Dict[str, str]:
    """
    Retrieve all environment variables from AWS Secrets Manager and cache them.
    """
    if secret_name in secrets_cache:
        return secrets_cache[secret_name]

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        secrets_cache[secret_name] = secret
        logger.debug("Secrets loaded and cached successfully.")
        return secret
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        return {}


secrets = get_all_secrets()


def get_env_var(key: str, default: str = None) -> str:
    """
    Get environment variable from secrets or `.env` with a fallback to default.
    """
    return secrets.get(key) or os.getenv(key, default)


CLIENT_ID = get_env_var("CLIENT_ID")
CLIENT_SECRET = get_env_var("CLIENT_SECRET")
TOKEN_URL = get_env_var("TOKEN_URL", "https://sandbox-oauth.gouv.fr/api/oauth/token")
BASE_URL = get_env_var(
    "BASE_URL", "https://sandbox-api.gouv.fr/dila/legifrance/lf-engine-app"
)
OPENAI_API_KEY = get_env_var("OPENAI_API_KEY")
MISTRAL_API_KEY = get_env_var("MISTRAL_API_KEY")
ACCESS_TOKEN = get_env_var("ACCESS_TOKEN")
DYNAMO_TABLE_NAME = get_env_var("DYNAMO_TABLE_NAME")

api_client = LegifranceApiClient(
    base_url=BASE_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_url=TOKEN_URL,
)
