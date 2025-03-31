import time
from typing import Optional

import requests

from app.models.publisher import (
    HttpUrl,
    MediaCreationResponse,
    MediaPayload,
    PublishResponse,
    StatusResponse,
)


class Publisher:
    def __init__(self, access_token: str, api_version: str = "v22.0"):
        self.access_token = access_token
        self.api_version = api_version
        self.instagram_graph_url = f"https://graph.instagram.com/{api_version}"
        self.ig_user_id: Optional[str] = None
        self._get_instagram_user_id()

    def _get_instagram_user_id(self) -> str:
        params = {"fields": "id", "access_token": self.access_token}
        try:
            response = requests.get(f"{self.instagram_graph_url}/me", params=params)
            response.raise_for_status()
            ig_user_response = response.json()
            self.ig_user_id = ig_user_response.get("id")
            if not self.ig_user_id:
                raise ValueError("Error: Unable to retrieve Instagram User ID.")
            return self.ig_user_id
        except Exception as e:
            raise ValueError(f"Error retrieving Instagram User ID: {e}")

    def create_media_object(self, image_url: HttpUrl, caption: str) -> str:
        media_payload = MediaPayload(image_url=image_url, caption=caption)
        media_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media"
        params = {"access_token": self.access_token}
        try:
            response = requests.post(
                media_url, params=params, json=media_payload.model_dump(mode="json")
            )
            response.raise_for_status()
            creation_response = MediaCreationResponse(**response.json())
            return creation_response.id
        except Exception as e:
            raise ValueError(f"Error creating media object: {e}")

    def wait_for_media_processing(
        self, creation_id: str, max_attempts: int = 10, sleep_interval: int = 5
    ) -> str:
        attempts = 0
        while attempts < max_attempts:
            time.sleep(sleep_interval)
            status_url = f"{self.instagram_graph_url}/{creation_id}"
            params = {"fields": "status_code", "access_token": self.access_token}
            try:
                response = requests.get(status_url, params=params)
                response.raise_for_status()
                status_response = StatusResponse(**response.json())
                if status_response.status_code == "FINISHED":
                    return status_response.status_code
                attempts += 1
            except Exception as e:
                raise ValueError(f"Error checking media status: {e}")
        raise ValueError("Media processing not completed or failed.")

    def publish_post(self, creation_id: str) -> str:
        publish_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": self.access_token,
        }
        try:
            response = requests.post(publish_url, data=publish_payload)
            response.raise_for_status()
            publish_response = PublishResponse(**response.json())
            return publish_response.id
        except Exception as e:
            raise ValueError(f"Error publishing Instagram post: {e}")

    def publish(self, image_url: HttpUrl, caption: str) -> str:
        creation_id = self.create_media_object(image_url, caption)
        self.wait_for_media_processing(creation_id)
        return self.publish_post(creation_id)

    def comment_on_post(self, media_id: str, message: str) -> str:
        """
        Comment on an existing Instagram post.

        Args:
            media_id (str): The ID of the media (post) to comment on.
            message (str): The comment message.

        Returns:
            str: The ID of the created comment.

        Raises:
            ValueError: If the comment fails.
        """
        comment_url = f"{self.instagram_graph_url}/{media_id}/comments"
        payload = {"message": message, "access_token": self.access_token}
        try:
            response = requests.post(comment_url, data=payload)
            response.raise_for_status()
            comment_data = response.json()
            return comment_data.get("id")
        except Exception as e:
            raise ValueError(f"Error posting comment on media {media_id}: {e}")
