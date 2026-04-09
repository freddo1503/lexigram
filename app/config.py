import json
import logging
import os
from functools import cached_property
from pathlib import Path
from typing import Any, Optional, Tuple

import boto3
import dotenv
import yaml
from pydantic import Field, SecretStr, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pylegifrance import ApiConfig, LegifranceClient

dotenv.load_dotenv()

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp")
os.environ.setdefault("HOME", "/tmp")

logger = logging.getLogger(__name__)

AWS_SECRET_NAME = "my-env-secrets"


class AWSSecretsManagerSource(PydanticBaseSettingsSource):
    """Pydantic settings source that reads from AWS Secrets Manager."""

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        self._secrets: dict[str, str] = {}
        try:
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=AWS_SECRET_NAME)
            self._secrets = json.loads(response["SecretString"])
            logger.debug(
                "Loaded secrets from AWS Secrets Manager ('%s')", AWS_SECRET_NAME
            )
        except Exception as e:
            logger.warning(
                "AWS Secrets Manager unavailable ('%s'): %s", AWS_SECRET_NAME, e
            )

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> Tuple[Any, str, bool]:
        value = self._secrets.get(field_name)
        if value is None:
            value = self._secrets.get(field_name.upper())
        return value, field_name, False

    def __call__(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for field_name, field_info in self.settings_cls.model_fields.items():
            value, key, _ = self.get_field_value(field_info, field_name)
            if value is not None:
                d[key] = value
        return d


class LexigramSettings(BaseSettings):
    """Lexigram application settings with Pydantic validation."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")

    # Legifrance API configuration
    legifrance_client_id: Optional[str] = Field(
        default=None, description="Legifrance API client ID"
    )
    legifrance_client_secret: Optional[SecretStr] = Field(
        default=None, description="Legifrance API client secret"
    )

    # AI configuration
    mistral_api_key: Optional[SecretStr] = Field(
        default=None, description="Mistral API key"
    )
    default_llm_model: str = Field(
        default="mistral/mistral-large-latest",
        description="Default LLM model for CrewAI agents",
    )
    mistral_image_model: str = Field(
        default="mistral-medium-latest",
        description="Mistral model for image generation",
    )

    # Instagram configuration
    instagram_access_token: Optional[SecretStr] = Field(
        default=None, description="Instagram long-lived user access token"
    )
    instagram_app_id: Optional[str] = Field(
        default=None, description="Instagram App ID"
    )
    instagram_app_secret: Optional[SecretStr] = Field(
        default=None, description="Instagram App Secret"
    )
    instagram_api_version: str = Field(
        default="v23.0", description="Instagram/Facebook Graph API version"
    )

    # AWS infrastructure (no defaults — always from env/secrets)
    aws_region: Optional[str] = Field(default=None, description="AWS region")
    dynamo_table_name: Optional[str] = Field(
        default=None, description="DynamoDB table name"
    )
    s3_bucket_name: Optional[str] = Field(
        default=None, description="S3 bucket name for generated images"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            AWSSecretsManagerSource(settings_cls),
        )


class SettingsManager:
    """Manages application settings and provides lazy access to API clients."""

    def __init__(self):
        self._settings = LexigramSettings()
        logger.setLevel(self._settings.log_level)

    def refresh_instagram_token(self) -> None:
        """Refresh Instagram token if app credentials are available.

        Must be called explicitly (e.g. from main()) — NOT at import time —
        to avoid import-time network side effects.
        """
        s = self._settings
        if not (
            s.instagram_app_id and s.instagram_app_secret and s.instagram_access_token
        ):
            return

        from app.services.instagram_auth import get_refreshed_instagram_token

        try:
            refreshed = get_refreshed_instagram_token(
                app_id=s.instagram_app_id,
                app_secret=s.instagram_app_secret.get_secret_value(),
                current_token=s.instagram_access_token.get_secret_value(),
            )
            s.instagram_access_token = SecretStr(refreshed)
            logger.info("Instagram token validated/refreshed successfully")
        except Exception:
            logger.exception("Instagram token refresh failed, using existing token")

    @property
    def settings(self) -> LexigramSettings:
        """Get the current settings instance."""
        return self._settings

    @cached_property
    def api_config(self) -> ApiConfig:
        """Get the API config instance, creating it on first access."""
        s = self._settings
        if not (s.legifrance_client_id and s.legifrance_client_secret):
            raise ValueError(
                "Legifrance credentials missing: LEGIFRANCE_CLIENT_ID and "
                "LEGIFRANCE_CLIENT_SECRET must be set."
            )
        return ApiConfig(
            client_id=s.legifrance_client_id,
            client_secret=s.legifrance_client_secret.get_secret_value(),
        )

    @cached_property
    def api_client(self) -> LegifranceClient:
        """Get the API client instance, creating it on first access."""
        return LegifranceClient(self.api_config)


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
        logger.debug("Agents configuration loaded from %s", AGENTS_CONFIG_PATH)
        return config
    except Exception as e:
        logger.error(
            "Error loading agents configuration from %s: %s", AGENTS_CONFIG_PATH, e
        )
        return {"agents": {}, "tasks": {}}


agents_config = load_agents_config()
