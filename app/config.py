import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import boto3
import dotenv
import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pylegifrance import ApiConfig, LegifranceClient

dotenv.load_dotenv()

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp")

# Setup logging
logger = logging.getLogger(__name__)


class LexigramSettings(BaseSettings):
    """Lexigram application settings with Pydantic validation."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")

    # AWS Secrets Manager configuration
    aws_secret_name: str = Field(
        default="my-env-secrets", description="AWS Secrets Manager secret name"
    )

    # Legifrance API configuration
    legifrance_client_id: Optional[str] = Field(
        default=None, description="Legifrance API client ID"
    )
    legifrance_client_secret: Optional[str] = Field(
        default=None, description="Legifrance API client secret"
    )

    # AI API keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    mistral_api_key: Optional[str] = Field(default=None, description="Mistral API key")

    # Application tokens
    access_token: Optional[str] = Field(
        default=None, description="Application access token"
    )

    # DynamoDB configuration
    dynamo_table_name: Optional[str] = Field(
        default=None, description="DynamoDB table name"
    )

    # Instagram configuration
    instagram_app_id: str = Field(
        default="1290296265534782", description="Instagram App ID"
    )
    instagram_app_secret: Optional[str] = Field(
        default=None, description="Instagram App Secret"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


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


class SettingsManager:
    """Manages application settings with AWS Secrets Manager integration."""

    def __init__(self):
        self._settings = LexigramSettings()
        self._load_secrets()
        self._api_config = None
        self._api_client = None

        # Configure logging
        logger.setLevel(self._settings.log_level)

    def _load_secrets(self) -> None:
        """Load secrets from AWS Secrets Manager and update settings."""
        secrets = get_all_secrets(secret_name=self._settings.aws_secret_name)

        if secrets:
            settings_dict = self._settings.model_dump()
            for secret_key, secret_value in secrets.items():
                # Convert to snake_case to match pydantic field names
                field_name = secret_key.lower()
                if field_name in settings_dict and settings_dict[field_name] is None:
                    setattr(self._settings, field_name, secret_value)

                # Also set as environment variable for pylegifrance
                if field_name == "legifrance_client_id":
                    os.environ["LEGIFRANCE_CLIENT_ID"] = secret_value
                elif field_name == "legifrance_client_secret":
                    os.environ["LEGIFRANCE_CLIENT_SECRET"] = secret_value

    @property
    def settings(self) -> LexigramSettings:
        """Get the current settings instance."""
        return self._settings

    @property
    def api_config(self) -> ApiConfig:
        """Get the API config instance, creating it if needed."""
        if self._api_config is None:
            self._api_config = ApiConfig.from_env()
        return self._api_config

    @property
    def api_client(self) -> LegifranceClient:
        """Get the API client instance, creating it if needed."""
        if self._api_client is None:
            self._api_client = LegifranceClient(self.api_config)
        return self._api_client


# Initialize the settings manager
settings_manager = SettingsManager()
settings = settings_manager.settings


# Lazy access to API config and client - accessed when needed
def get_api_config() -> ApiConfig:
    """Get the API config instance."""
    return settings_manager.api_config


def get_api_client() -> LegifranceClient:
    """Get the API client instance."""
    return settings_manager.api_client


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
