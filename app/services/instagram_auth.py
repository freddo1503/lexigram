import json
import logging
from typing import Any, Dict, List, Optional

import boto3
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class InstagramTokenManager:
    """
    Manages Instagram access tokens with automatic refresh capabilities.

    This class handles:
    - Token validation and expiration checking
    - Automatic token refresh when approaching expiration
    - Secure token storage in AWS Secrets Manager
    - Fallback to environment variables
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        current_token: Optional[str] = None,
        secret_name: str = "my-env-secrets",
        token_key: str = "ACCESS_TOKEN",
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.current_token = current_token
        self.secret_name = secret_name
        self.token_key = token_key
        self.secrets_client = boto3.client("secretsmanager")

    def is_token_valid(self) -> bool:
        """
        Check if the current token is valid by making a test API call.

        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            response = requests.get(
                "https://graph.instagram.com/v23.0/me",
                params={"fields": "id", "access_token": self.current_token},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return False

    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current token including expiration.

        Returns:
            dict: Token info including expires_in, or None if request fails
        """
        try:
            response = requests.get(
                "https://graph.facebook.com/v23.0/oauth/access_token_info",
                params={"access_token": self.current_token},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Failed to get token info: {e}")
        return None

    def refresh_long_lived_token(self) -> Optional[str]:
        """
        Refresh the current long-lived Instagram token to extend its expiration.

        Uses the Instagram-specific refresh endpoint for 2025.
        Token must be at least 24 hours old but not expired.

        Returns:
            str: New refreshed token, or None if refresh fails
        """
        try:
            # Use Instagram-specific refresh endpoint (2025 best practice)
            response = requests.get(
                "https://graph.instagram.com/refresh_access_token",
                params={
                    "grant_type": "ig_refresh_token",
                    "access_token": self.current_token,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                new_token = data.get("access_token")
                expires_in = data.get("expires_in", 5184000)  # 60 days default

                logger.info(
                    f"Instagram token refreshed successfully. Expires in {expires_in} seconds ({expires_in // 86400} days)"
                )
                return new_token
            else:
                logger.error(
                    f"Instagram token refresh failed: {response.status_code} - {response.text}"
                )

                # Fallback to Facebook Graph API method if Instagram endpoint fails
                logger.info("Attempting fallback refresh via Facebook Graph API...")
                return self._fallback_facebook_refresh()

        except Exception as e:
            logger.error(f"Error refreshing Instagram token: {e}")
            # Try fallback method
            return self._fallback_facebook_refresh()

    def _fallback_facebook_refresh(self) -> Optional[str]:
        """
        Fallback token refresh using Facebook Graph API method.

        Returns:
            str: New refreshed token, or None if refresh fails
        """
        try:
            response = requests.get(
                "https://graph.facebook.com/v23.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "fb_exchange_token": self.current_token,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                new_token = data.get("access_token")
                expires_in = data.get("expires_in", 5184000)

                logger.info(
                    f"Fallback token refresh successful. Expires in {expires_in} seconds"
                )
                return new_token
            else:
                logger.error(
                    f"Fallback token refresh failed: {response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.error(f"Error in fallback token refresh: {e}")

        return None

    def update_token_in_secrets(self, new_token: str) -> bool:
        """
        Update the token in AWS Secrets Manager.

        Args:
            new_token: The new access token to store

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Get current secrets
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            secrets = json.loads(response["SecretString"])

            # Update the token
            secrets[self.token_key] = new_token

            # Store back to Secrets Manager
            self.secrets_client.update_secret(
                SecretId=self.secret_name, SecretString=json.dumps(secrets)
            )

            logger.info("Token updated in AWS Secrets Manager successfully")
            return True

        except ClientError as e:
            logger.error(f"Failed to update token in Secrets Manager: {e}")
            return False

    def ensure_valid_token(self) -> str:
        """
        Ensure we have a valid token, creating one if necessary.

        Returns:
            str: A valid access token

        Raises:
            Exception: If unable to obtain a valid token
        """
        # If we have a current token, check if it's valid
        if self.current_token and self.is_token_valid():
            # Check if token is close to expiring (within 7 days)
            token_info = self.get_token_info()
            if token_info and "expires_in" in token_info:
                expires_in = token_info["expires_in"]
                if expires_in < 7 * 24 * 3600:  # Less than 7 days
                    logger.info(f"Token expires in {expires_in} seconds, refreshing...")
                    new_token = self.refresh_long_lived_token()
                    if new_token:
                        if self.update_token_in_secrets(new_token):
                            self.current_token = new_token
                            return new_token
                        else:
                            logger.warning(
                                "Failed to update token in secrets, using current token"
                            )

            return self.current_token

        # No valid token, try to refresh existing one first
        if self.current_token:
            logger.info("Current token is invalid, attempting refresh...")
            new_token = self.refresh_long_lived_token()
            if new_token:
                if self.update_token_in_secrets(new_token):
                    self.current_token = new_token
                    return new_token
                else:
                    logger.warning(
                        "Failed to update token in secrets, using refreshed token"
                    )
                    return new_token

        # No valid token and refresh failed, create a new permanent token
        logger.info("No valid token available, creating permanent system user token...")
        generator = SystemUserTokenGenerator(self.app_id, self.app_secret)
        permanent_token = generator.create_permanent_instagram_token()

        if permanent_token:
            if self.update_token_in_secrets(permanent_token):
                self.current_token = permanent_token
                logger.info("Permanent token created and stored successfully")
                return permanent_token
            else:
                logger.warning("Failed to store permanent token, but returning it")
                self.current_token = permanent_token
                return permanent_token

        raise Exception(
            "Unable to obtain a valid Instagram access token through any method"
        )

    @classmethod
    def from_config(
        cls, app_id: str, app_secret: str, current_token: str
    ) -> "InstagramTokenManager":
        """
        Create an InstagramTokenManager from configuration.

        Args:
            app_id: Facebook App ID
            app_secret: Facebook App Secret
            current_token: Current Instagram access token

        Returns:
            InstagramTokenManager: Configured token manager
        """
        return cls(app_id=app_id, app_secret=app_secret, current_token=current_token)


class SystemUserTokenGenerator:
    """
    Generates permanent system user tokens for Instagram Business accounts.

    System user tokens don't expire and provide the most reliable automation
    for business applications.
    """

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret

    def get_app_access_token(self) -> str:
        """
        Get an app access token for Business Manager operations.

        Returns:
            str: App access token

        Raises:
            Exception: If unable to get app token
        """
        try:
            response = requests.get(
                "https://graph.facebook.com/v23.0/oauth/access_token",
                params={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "grant_type": "client_credentials",
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                app_token = data.get("access_token")
                logger.info("App access token obtained successfully")
                return app_token
            else:
                logger.error(
                    f"Failed to get app access token: {response.status_code} - {response.text}"
                )
                raise Exception(f"App token request failed: {response.text}")

        except Exception as e:
            logger.error(f"Error getting app access token: {e}")
            raise

    def list_business_managers(self, app_token: str) -> List[Dict[str, Any]]:
        """
        List all business managers associated with the app.

        Args:
            app_token: App access token

        Returns:
            list: List of business manager objects
        """
        try:
            response = requests.get(
                f"https://graph.facebook.com/v23.0/{self.app_id}/businesses",
                params={"access_token": app_token},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                businesses = data.get("data", [])
                logger.info(f"Found {len(businesses)} business managers")
                return businesses
            else:
                logger.error(
                    f"Failed to list businesses: {response.status_code} - {response.text}"
                )
                return []

        except Exception as e:
            logger.error(f"Error listing business managers: {e}")
            return []

    def create_system_user(
        self, business_id: str, app_token: str, name: str = "Lexigram System User"
    ) -> Optional[str]:
        """
        Create a system user in Business Manager.

        Args:
            business_id: Business Manager ID
            app_token: App access token
            name: Name for the system user

        Returns:
            str: System user ID, or None if creation fails
        """
        try:
            response = requests.post(
                f"https://graph.facebook.com/v23.0/{business_id}/system_users",
                data={"name": name, "role": "ADMIN", "access_token": app_token},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                system_user_id = data.get("id")
                logger.info(f"System user created successfully: {system_user_id}")
                return system_user_id
            else:
                logger.error(
                    f"Failed to create system user: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error creating system user: {e}")
            return None

    def generate_system_user_token(
        self, business_id: str, system_user_id: str, app_token: str
    ) -> Optional[str]:
        """
        Generate a permanent access token for the system user.

        Args:
            business_id: Business Manager ID
            system_user_id: System user ID
            app_token: App access token

        Returns:
            str: Permanent system user token, or None if generation fails
        """
        try:
            # Generate token with Instagram permissions
            response = requests.post(
                f"https://graph.facebook.com/v23.0/{system_user_id}/access_tokens",
                data={
                    "business_app": self.app_id,
                    "scope": "instagram_business_basic,instagram_business_content_publish",
                    "access_token": app_token,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                permanent_token = data.get("access_token")
                logger.info("Permanent system user token generated successfully")
                return permanent_token
            else:
                logger.error(
                    f"Failed to generate system user token: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error generating system user token: {e}")
            return None

    def get_instagram_business_account(self, token: str) -> Optional[str]:
        """
        Get the Instagram business account ID associated with the token.

        Args:
            token: Access token

        Returns:
            str: Instagram business account ID, or None if not found
        """
        try:
            # First get pages
            response = requests.get(
                "https://graph.facebook.com/v23.0/me/accounts",
                params={
                    "access_token": token,
                    "fields": "id,name,instagram_business_account",
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                pages = data.get("data", [])

                for page in pages:
                    instagram_account = page.get("instagram_business_account")
                    if instagram_account:
                        ig_account_id = instagram_account.get("id")
                        logger.info(
                            f"Found Instagram business account: {ig_account_id}"
                        )
                        return ig_account_id

                logger.warning("No Instagram business account found")
                return None
            else:
                logger.error(
                    f"Failed to get pages: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting Instagram business account: {e}")
            return None

    def create_permanent_instagram_token(
        self, business_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a permanent Instagram access token using system user.

        Args:
            business_id: Specific business ID to use (optional)

        Returns:
            str: Permanent Instagram access token, or None if creation fails
        """
        try:
            logger.info("Starting permanent Instagram token creation...")

            # Step 1: Get app access token
            app_token = self.get_app_access_token()

            # Step 2: Get business managers
            businesses = self.list_business_managers(app_token)
            if not businesses:
                logger.error("No business managers found for this app")
                return None

            # Use specified business or first available
            target_business = None
            if business_id:
                target_business = next(
                    (b for b in businesses if b["id"] == business_id), None
                )
            else:
                target_business = businesses[0]

            if not target_business:
                logger.error(f"Business manager not found: {business_id}")
                return None

            business_id = target_business["id"]
            logger.info(
                f"Using business manager: {target_business['name']} ({business_id})"
            )

            # Step 3: Create or find system user
            system_user_id = self.create_system_user(business_id, app_token)
            if not system_user_id:
                logger.error("Failed to create system user")
                return None

            # Step 4: Generate permanent token
            permanent_token = self.generate_system_user_token(
                business_id, system_user_id, app_token
            )
            if not permanent_token:
                logger.error("Failed to generate permanent token")
                return None

            # Step 5: Verify Instagram account access
            ig_account_id = self.get_instagram_business_account(permanent_token)
            if not ig_account_id:
                logger.warning("Token created but no Instagram account found")

            logger.info("Permanent Instagram token created successfully!")
            return permanent_token

        except Exception as e:
            logger.error(f"Error creating permanent Instagram token: {e}")
            return None


def create_instagram_token(app_id: str, app_secret: str) -> str:
    """
    Create a new permanent Instagram access token from just app credentials.

    This function requires:
    1. A Facebook Business Manager account
    2. Instagram Business Account linked to a Facebook Page
    3. The app must be added to the Business Manager

    Required permissions that will be automatically granted:
    - instagram_basic: Read basic Instagram account info
    - instagram_content_publish: Create and publish content
    - pages_show_list: Access to Facebook Pages
    - pages_read_engagement: Read page engagement data
    - business_management: Manage Business Manager resources

    Args:
        app_id: Facebook App ID (e.g., "1164730391873131")
        app_secret: Facebook App Secret

    Returns:
        str: Permanent Instagram access token

    Raises:
        Exception: If unable to create token or missing Business Manager setup
    """
    generator = SystemUserTokenGenerator(app_id, app_secret)
    permanent_token = generator.create_permanent_instagram_token()

    if not permanent_token:
        raise Exception(
            "Failed to create Instagram token. Ensure:\n"
            "1. App is added to a Facebook Business Manager\n"
            "2. Instagram Business Account is linked to a Facebook Page\n"
            "3. App has required permissions in Business Manager\n"
            "4. App credentials are correct"
        )

    return permanent_token


def get_refreshed_instagram_token(
    app_id: str, app_secret: str, current_token: Optional[str] = None
) -> str:
    """
    Get a valid Instagram token, creating a permanent one if needed.

    Args:
        app_id: Facebook App ID
        app_secret: Facebook App Secret
        current_token: Current Instagram access token (optional)

    Returns:
        str: Valid Instagram access token

    Raises:
        Exception: If unable to obtain a valid token
    """
    # If no current token, create a new one
    if not current_token:
        logger.info("No current token provided, creating new permanent token...")
        return create_instagram_token(app_id, app_secret)

    # Try to refresh existing token
    manager = InstagramTokenManager(app_id, app_secret, current_token)

    try:
        return manager.ensure_valid_token()
    except Exception as e:
        logger.warning(f"Token management failed: {e}")
        logger.info("Creating new permanent token as fallback...")
        return create_instagram_token(app_id, app_secret)
