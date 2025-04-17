import logging
import time
from typing import Optional

from app.errors.exceptions import (
    AuthenticationError,
    DataParsingError,
    InstagramError,
    PublishingError,
    RateLimitError,
)
from app.errors.handlers import retry, safe_parse_json, safe_request
from app.models.publisher import (
    HttpUrl,
    MediaCreationResponse,
    MediaPayload,
    PublishResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)


class Publisher:
    def __init__(self, access_token: str, api_version: str = "v22.0"):
        self.access_token = access_token
        self.api_version = api_version
        self.instagram_graph_url = f"https://graph.instagram.com/{api_version}"
        self.ig_user_id: Optional[str] = None
        self._get_instagram_user_id()

    @retry(max_attempts=3)
    def _get_instagram_user_id(self) -> str:
        """
        Retrieve the Instagram User ID associated with the access token.

        Returns:
            str: The Instagram User ID.

        Raises:
            AuthenticationError: If authentication with Instagram fails.
            InstagramError: For other Instagram-specific errors.
        """
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
            self.ig_user_id = ig_user_response.get("id")

            if not self.ig_user_id:
                raise AuthenticationError(
                    "Unable to retrieve Instagram User ID",
                    details={"response": ig_user_response},
                )

            logger.info("Successfully retrieved Instagram User ID: %s", self.ig_user_id)
            return self.ig_user_id

        except Exception as e:
            if not isinstance(e, (AuthenticationError, DataParsingError)):
                raise InstagramError(
                    f"Error retrieving Instagram User ID: {str(e)}",
                    original_exception=e,
                ) from e
            raise

    @retry(max_attempts=3)
    def create_media_object(self, image_url: HttpUrl, caption: str) -> str:
        """
        Create a media object on Instagram.

        Args:
            image_url: URL of the image to post.
            caption: Caption for the post.

        Returns:
            str: The ID of the created media object.

        Raises:
            PublishingError: If media creation fails.
            InstagramError: For other Instagram-specific errors.
        """
        try:
            media_payload = MediaPayload(image_url=image_url, caption=caption)
            media_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media"
            params = {"access_token": self.access_token}

            logger.info(
                "Creating Instagram media object with caption: %s",
                caption[:30] + "..." if len(caption) > 30 else caption,
            )

            response = safe_request(
                "POST",
                media_url,
                api_name="Instagram",
                params=params,
                json=media_payload.model_dump(mode="json"),
            )

            response_data = safe_parse_json(response, api_name="Instagram")

            try:
                creation_response = MediaCreationResponse(**response_data)
                logger.info(
                    "Successfully created Instagram media object with ID: %s",
                    creation_response.id,
                )
                return creation_response.id
            except Exception as e:
                raise DataParsingError(
                    "Failed to parse Instagram media creation response",
                    original_exception=e,
                    details={"response": response_data},
                )

        except Exception as e:
            if not isinstance(e, (DataParsingError, RateLimitError)):
                raise PublishingError(
                    f"Error creating Instagram media object: {str(e)}",
                    original_exception=e,
                    details={
                        "image_url": str(image_url),
                        "caption_length": len(caption),
                    },
                ) from e
            raise

    def wait_for_media_processing(
        self, creation_id: str, max_attempts: int = 10, sleep_interval: int = 5
    ) -> str:
        """
        Wait for media processing to complete on Instagram.

        Args:
            creation_id: ID of the media being processed.
            max_attempts: Maximum number of status check attempts.
            sleep_interval: Time to wait between status checks in seconds.

        Returns:
            str: The status code of the processed media.

        Raises:
            PublishingError: If media processing fails or times out.
            InstagramError: For other Instagram-specific errors.
        """
        attempts = 0
        while attempts < max_attempts:
            time.sleep(sleep_interval)
            status_url = f"{self.instagram_graph_url}/{creation_id}"
            params = {"fields": "status_code", "access_token": self.access_token}

            try:
                logger.info(
                    "Checking media processing status (attempt %d/%d)",
                    attempts + 1,
                    max_attempts,
                )

                response = safe_request(
                    "GET", status_url, api_name="Instagram", params=params
                )

                response_data = safe_parse_json(response, api_name="Instagram")

                try:
                    status_response = StatusResponse(**response_data)
                    logger.info(
                        "Media processing status: %s", status_response.status_code
                    )

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
                except Exception as e:
                    if not isinstance(e, PublishingError):
                        raise DataParsingError(
                            "Failed to parse Instagram status response",
                            original_exception=e,
                            details={"response": response_data},
                        )
                    raise

                attempts += 1
            except Exception as e:
                if not isinstance(
                    e, (DataParsingError, RateLimitError, PublishingError)
                ):
                    raise InstagramError(
                        f"Error checking Instagram media status: {str(e)}",
                        original_exception=e,
                        details={"creation_id": creation_id, "attempt": attempts + 1},
                    ) from e
                raise

        # If we've exhausted all attempts
        raise PublishingError(
            "Instagram media processing timed out",
            details={
                "creation_id": creation_id,
                "max_attempts": max_attempts,
                "total_wait_time": max_attempts * sleep_interval,
            },
        )

    @retry(max_attempts=3)
    def publish_post(self, creation_id: str) -> str:
        """
        Publish a media object as a post on Instagram.

        Args:
            creation_id: ID of the media to publish.

        Returns:
            str: The ID of the published post.

        Raises:
            PublishingError: If publishing fails.
            InstagramError: For other Instagram-specific errors.
        """
        try:
            publish_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token,
            }

            logger.info("Publishing Instagram post with creation ID: %s", creation_id)

            response = safe_request(
                "POST", publish_url, api_name="Instagram", data=publish_payload
            )

            response_data = safe_parse_json(response, api_name="Instagram")

            try:
                publish_response = PublishResponse(**response_data)
                logger.info(
                    "Successfully published Instagram post with ID: %s",
                    publish_response.id,
                )
                return publish_response.id
            except Exception as e:
                raise DataParsingError(
                    "Failed to parse Instagram publish response",
                    original_exception=e,
                    details={"response": response_data},
                )

        except Exception as e:
            if not isinstance(e, (DataParsingError, RateLimitError)):
                raise PublishingError(
                    f"Error publishing Instagram post: {str(e)}",
                    original_exception=e,
                    details={"creation_id": creation_id},
                ) from e
            raise

    def publish(self, image_url: HttpUrl, caption: str) -> str:
        creation_id = self.create_media_object(image_url, caption)
        self.wait_for_media_processing(creation_id)
        return self.publish_post(creation_id)

    @retry(max_attempts=3)
    def comment_on_post(self, media_id: str, message: str) -> str:
        """
        Comment on an existing Instagram post.

        Args:
            media_id: The ID of the media (post) to comment on.
            message: The comment message.

        Returns:
            str: The ID of the created comment.

        Raises:
            PublishingError: If commenting fails.
            InstagramError: For other Instagram-specific errors.
        """
        try:
            comment_url = f"{self.instagram_graph_url}/{media_id}/comments"
            payload = {"message": message, "access_token": self.access_token}

            logger.info("Posting comment on Instagram media ID: %s", media_id)

            response = safe_request(
                "POST", comment_url, api_name="Instagram", data=payload
            )

            comment_data = safe_parse_json(response, api_name="Instagram")
            comment_id = comment_data.get("id")

            if not comment_id:
                raise DataParsingError(
                    "Failed to get comment ID from Instagram response",
                    details={"response": comment_data},
                )

            logger.info("Successfully posted comment with ID: %s", comment_id)
            return comment_id

        except Exception as e:
            if not isinstance(e, (DataParsingError, RateLimitError)):
                raise PublishingError(
                    f"Error posting comment on Instagram media {media_id}: {str(e)}",
                    original_exception=e,
                    details={"media_id": media_id, "message_length": len(message)},
                ) from e
            raise
