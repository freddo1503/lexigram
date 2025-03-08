import json
import time

import requests


class Publisher:
    def __init__(self, access_token, api_version="v22.0"):
        """
        Initialize the Instagram Publisher with authentication details.

        Args:
            access_token: Instagram API access token
            api_version: Instagram Graph API version to use (defaults to v22.0)
        """
        self.access_token = access_token
        self.api_version = api_version
        self.instagram_graph_url = f"https://graph.instagram.com/{api_version}"
        self.ig_user_id = None

        self._get_instagram_user_id()

    def _get_instagram_user_id(self):
        """Retrieve the correct Instagram User ID"""
        print("Retrieving correct Instagram User ID...")
        params = {"fields": "id", "access_token": self.access_token}
        try:
            response = requests.get(f"{self.instagram_graph_url}/me", params=params)
            response.raise_for_status()
        except Exception as e:
            print(f"Error retrieving Instagram User ID: {e}")
            raise

        ig_user_response = response.json()
        self.ig_user_id = ig_user_response.get("id")

        if not self.ig_user_id:
            raise ValueError("Error: Unable to retrieve Instagram User ID.")

        return self.ig_user_id

    def create_media_object(self, image_url: str, caption: str):
        """
        Create a media object with the provided image URL and caption.

        Args:
            image_url: URL of the image to post
            caption: Caption text for the post

        Returns:media_payload
            creation_id: The ID of the created media object
        """
        media_payload = {"image_url": image_url, "caption": caption}
        print("Creating media object... \n", json.dumps(media_payload, indent=4))
        media_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media"
        params = {"access_token": self.access_token}

        try:
            response = requests.post(media_url, params=params, json=media_payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Error creating media object: {e}")
            raise

        creation_response = response.json()
        print(f"Media creation response: {creation_response}")
        creation_id = creation_response.get("id")

        if not creation_id:
            error_message = creation_response.get("error", {}).get(
                "message", "Unknown error"
            )
            raise ValueError(f"Error creating media object: {error_message}")

        print(f"Media object created successfully: {creation_id}")
        return creation_id

    def wait_for_media_processing(self, creation_id, max_attempts=10, sleep_interval=5):
        """
        Wait for media object to be processed by Instagram.

        Args:
            creation_id: The ID of the created media object
            max_attempts: Maximum number of status check attempts
            sleep_interval: Number of seconds to wait between status checks

        Returns:
            status: Final status of the media object
        """
        status = "in_progress"
        attempts = 0

        print("Waiting for media processing...")
        while status == "in_progress" and attempts < max_attempts:
            time.sleep(sleep_interval)
            status_url = f"{self.instagram_graph_url}/{creation_id}"
            params = {"fields": "status_code", "access_token": self.access_token}

            try:
                response = requests.get(status_url, params=params)
                response.raise_for_status()
            except Exception as e:
                print(f"Error checking status: {e}")
                raise

            status_response = response.json()
            print(f"Status check response: {status_response}")
            status = status_response.get("status_code", "unknown")
            print(f"Current media status: {status}")
            attempts += 1

        if status != "FINISHED":
            raise ValueError(
                f"Error: Media processing not completed or failed. Status: {status}"
            )

        print("Media processing completed successfully. Proceeding to publish.")
        return status

    def publish_post(self, creation_id):
        """
        Publish the Instagram post using the media creation ID.

        Args:
            creation_id: The ID of the created media object

        Returns:
            published_id: The ID of the published post
        """
        print("Publishing Instagram post...")
        publish_url = f"{self.instagram_graph_url}/{self.ig_user_id}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": self.access_token,
        }

        try:
            response = requests.post(publish_url, data=publish_payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Error publishing Instagram post: {e}")
            raise

        publish_response = response.json()
        print(f"Publish response: {publish_response}")
        published_id = publish_response.get("id")

        if not published_id:
            error_message = publish_response.get("error", {}).get(
                "message", "Unknown error"
            )
            raise ValueError(f"Error publishing Instagram post: {error_message}")

        print(f"Instagram post published successfully. Post ID: {published_id}")
        return published_id

    def publish(self, image_url: str, caption: str):
        """
        Complete Instagram publishing process: create media, wait for processing, publish.

        Args:
            image_url: URL of the image to post
            caption: Caption text for the post

        Returns:
            published_id: The ID of the published post
        """
        # Create media object
        creation_id = self.create_media_object(image_url, caption)

        # Wait for processing
        self.wait_for_media_processing(creation_id)

        # Publish post
        published_id = self.publish_post(creation_id)

        return published_id
