import logging
import time
from typing import Any, Dict, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.errors.exceptions import (
    AuthenticationError,
    DataParsingError,
    InstagramError,
    PublishingError,
    RateLimitError,
)
from app.errors.handlers import safe_parse_json, safe_request
from app.models.publisher import (
    HttpUrl,
    MediaCreationResponse,
    MediaPayload,
    PublishResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)


class Publisher:
    def __init__(self, access_token: str, api_version: str):
        self.api_version = api_version
        self.instagram_graph_url = f"https://graph.instagram.com/{api_version}"
        self._ig_user_id: Optional[str] = None
        self.access_token = access_token

    @property
    def ig_user_id(self) -> Optional[str]:
        """Lazily resolve and cache the Instagram User ID on first access."""
        if self._ig_user_id is None:
            self._get_instagram_user_id()
        return self._ig_user_id

    def _instagram_api_call(
        self, method: str, url: str, operation: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Make an Instagram API call with consistent error handling.

        Returns parsed JSON response dict. Lets DataParsingError and
        RateLimitError propagate; wraps anything else in PublishingError.
        """
        try:
            response = safe_request(method, url, api_name="Instagram", **kwargs)
            return safe_parse_json(response, api_name="Instagram")
        except (DataParsingError, RateLimitError):
            raise
        except Exception as e:
            raise PublishingError(
                "Error in Instagram %s: %s" % (operation, e),
                original_exception=e,
            ) from e

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=60), reraise=True
    )
    def _get_instagram_user_id(self) -> str:
        """Retrieve the Instagram User ID associated with the access token."""
        params = {"fields": "id", "access_token": self.access_token}

        try:
            logger.info("Retrieving Instagram User ID")
            response = safe_request(
                "GET",
                f"{self.instagram_graph_url}/me",
                api_name="Instagram",
                params=params,
            )

            ig_user_response = safe_parse_json(response, api_name="Instagram")
            self._ig_user_id = ig_user_response.get("id")

            if not self._ig_user_id:
                raise AuthenticationError(
                    "Unable to retrieve Instagram User ID",
                    details={"response": ig_user_response},
                )

            logger.info(
                "Successfully retrieved Instagram User ID: %s", self._ig_user_id
            )
            return self._ig_user_id

        except Exception as e:
            if not isinstance(e, (AuthenticationError, DataParsingError)):
                raise InstagramError(
                    "Error retrieving Instagram User ID: %s" % e,
                    original_exception=e,
                ) from e
            raise

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=60), reraise=True
    )
    def create_media_object(self, image_url: HttpUrl, caption: str) -> str:
        """Create a media object on Instagram."""
        media_payload = MediaPayload(image_url=image_url, caption=caption)
        media_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media"
        params = {
            "access_token": self.access_token,
            **media_payload.model_dump(mode="json"),
        }

        logger.info(
            "Creating Instagram media object with caption: %s",
            caption[:30] + "..." if len(caption) > 30 else caption,
        )

        response_data = self._instagram_api_call(
            "POST",
            media_url,
            "media creation",
            params=params,
        )

        try:
            creation_response = MediaCreationResponse(**response_data)
        except Exception as e:
            raise DataParsingError(
                "Failed to parse Instagram media creation response",
                original_exception=e,
                details={"response": response_data},
            )

        logger.info(
            "Successfully created Instagram media object with ID: %s",
            creation_response.id,
        )
        return creation_response.id

    def wait_for_media_processing(
        self, creation_id: str, max_attempts: int = 10, sleep_interval: int = 5
    ) -> str:
        """Wait for media processing to complete on Instagram."""
        status_url = f"{self.instagram_graph_url}/{creation_id}"
        params = {"fields": "status_code", "access_token": self.access_token}

        for attempt in range(1, max_attempts + 1):
            time.sleep(sleep_interval)
            logger.info(
                "Checking media processing status (attempt %d/%d)",
                attempt,
                max_attempts,
            )

            response_data = self._instagram_api_call(
                "GET",
                status_url,
                "status check",
                params=params,
            )

            try:
                status_response = StatusResponse(**response_data)
            except Exception as e:
                raise DataParsingError(
                    "Failed to parse Instagram status response",
                    original_exception=e,
                    details={"response": response_data},
                )

            logger.info("Media processing status: %s", status_response.status_code)

            if status_response.status_code == "FINISHED":
                return status_response.status_code
            elif status_response.status_code == "ERROR":
                raise PublishingError(
                    "Instagram media processing failed",
                    details={
                        "creation_id": creation_id,
                        "status": status_response.status_code,
                    },
                )

        raise PublishingError(
            "Instagram media processing timed out",
            details={
                "creation_id": creation_id,
                "max_attempts": max_attempts,
                "total_wait_time": max_attempts * sleep_interval,
            },
        )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=60), reraise=True
    )
    def publish_post(self, creation_id: str) -> str:
        """Publish a media object as a post on Instagram."""
        publish_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": self.access_token,
        }

        logger.info("Publishing Instagram post with creation ID: %s", creation_id)

        response_data = self._instagram_api_call(
            "POST",
            publish_url,
            "publish",
            data=publish_payload,
        )

        try:
            publish_response = PublishResponse(**response_data)
        except Exception as e:
            raise DataParsingError(
                "Failed to parse Instagram publish response",
                original_exception=e,
                details={"response": response_data},
            )

        logger.info(
            "Successfully published Instagram post with ID: %s",
            publish_response.id,
        )
        return publish_response.id

    def publish(self, image_url: HttpUrl, caption: str) -> str:
        creation_id = self.create_media_object(image_url, caption)
        self.wait_for_media_processing(creation_id)
        return self.publish_post(creation_id)
