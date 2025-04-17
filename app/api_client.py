import logging
import time
import typing as t

import requests

from app.errors.exceptions import (
    APIError,
    AuthenticationError,
    DataParsingError,
    LegifranceError,
)
from app.errors.handlers import retry, safe_parse_json, safe_request

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class LegifranceApiClient:
    def __init__(
        self,
        base_url: str,
        token: t.Optional[str] = None,
        client_id: t.Optional[str] = None,
        client_secret: t.Optional[str] = None,
        token_url: t.Optional[str] = None,
    ) -> None:
        """
        Initialize the API client.

        Args:
            base_url (str): The base URL of the API.
            token (Optional[str]): An existing access token.
            client_id (Optional[str]): Client ID for token retrieval.
            client_secret (Optional[str]): Client secret for token retrieval.
            token_url (Optional[str]): URL to retrieve the access token.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url

        if token:
            self.token = token
            self.token_expiry = None  # Not managed by the client
        else:
            if not (client_id and client_secret and token_url):
                raise ValueError(
                    "Either a token must be provided or client credentials and token_url must be specified."
                )
            self.token = self._get_access_token()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    @retry(max_attempts=3)
    def _get_access_token(self) -> str:
        """
        Retrieves an access token using client credentials and updates the token expiry.

        Returns:
            str: A valid access token.

        Raises:
            AuthenticationError: If authentication fails.
            DataParsingError: If the response cannot be parsed as JSON.
            LegifranceError: For other Legifrance-specific errors.
        """
        payload: t.Dict[str, t.Any] = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": "openid",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = safe_request(
                "POST",
                self._token_url,
                api_name="Legifrance Auth",
                data=payload,
                headers=headers,
            )
            token_data = safe_parse_json(response, api_name="Legifrance Auth")

            if (
                not token_data.get("access_token")
                or token_data.get("access_token") == "null"
            ):
                raise AuthenticationError(
                    "Failed to obtain access token", details={"response": token_data}
                )

            # Cache the token expiry; subtract a safety margin (e.g., 60 seconds)
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = time.time() + expires_in - 60
            return token_data.get("access_token")
        except APIError as e:
            # Wrap in LegifranceError if it's not already an AuthenticationError
            if not isinstance(e, AuthenticationError):
                raise LegifranceError(
                    f"Error obtaining Legifrance access token: {e.message}",
                    original_exception=e,
                    details=getattr(e, "details", {}),
                ) from e
            raise

    def _ensure_token(self) -> None:
        """
        Ensure the access token is valid and refresh it if expired.
        """
        if self.token_expiry and time.time() > self.token_expiry:
            logger.info("Access token expired, refreshing token...")
            self.token = self._get_access_token()
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _build_url(self, endpoint: str) -> str:
        """
        Build the full URL for an endpoint.
        """
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    @retry(max_attempts=3)
    def request(
        self,
        method: str,
        endpoint: str,
        payload: t.Optional[str] = None,
        params: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> t.Dict[str, t.Any]:
        """
        Send an HTTP request and return the JSON response.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint to request
            payload: Request payload (will be converted to JSON)
            params: Query parameters

        Returns:
            The JSON response as a dictionary

        Raises:
            LegifranceError: For Legifrance-specific errors
            AuthenticationError: If authentication fails
            DataParsingError: If the response cannot be parsed as JSON
            APIError: For other API-related errors
        """
        self._ensure_token()  # Refresh token if necessary
        url = self._build_url(endpoint)

        try:
            # Use our session for authentication headers
            headers = self.session.headers.copy()

            # Make the request with our safe_request utility
            response = safe_request(
                method,
                url,
                api_name="Legifrance",
                headers=headers,
                json=payload,
                params=params,
            )

            # Parse the JSON response safely
            return safe_parse_json(response, api_name="Legifrance")
        except APIError as e:
            # Wrap in LegifranceError if it's not already a specific error type
            if not isinstance(e, (AuthenticationError, DataParsingError)):
                raise LegifranceError(
                    f"Error in Legifrance API request: {e.message}",
                    original_exception=e,
                    details=getattr(e, "details", {}),
                ) from e
            raise

    @retry(max_attempts=3)
    def get(
        self,
        endpoint: str,
        params: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> t.Union[t.Dict[str, t.Any], str]:
        """
        Perform a GET request and return the response.

        Args:
            endpoint: API endpoint to request.
            params: Query parameters.

        Returns:
            The response content as a dictionary (if JSON) or string.

        Raises:
            LegifranceError: For Legifrance-specific errors
            AuthenticationError: If authentication fails
            APIError: For other API-related errors
        """
        self._ensure_token()  # Refresh token if necessary
        url = self._build_url(endpoint)

        try:
            # Use our session for authentication headers
            headers = self.session.headers.copy()

            # Make the request with our safe_request utility
            response = safe_request(
                "GET", url, api_name="Legifrance", headers=headers, params=params
            )

            # Try to parse as JSON, fall back to text
            try:
                return safe_parse_json(response, api_name="Legifrance")
            except DataParsingError:
                return response.text
        except APIError as e:
            # Wrap in LegifranceError if it's not already a specific error type
            if not isinstance(e, AuthenticationError):
                raise LegifranceError(
                    f"Error in Legifrance API GET request: {e.message}",
                    original_exception=e,
                    details=getattr(e, "details", {}),
                ) from e
            raise

    def post(
        self,
        endpoint: str,
        payload: t.Optional[str] = None,
    ) -> t.Dict[str, t.Any]:
        """
        Perform a POST request and return the JSON response.

        Args:
            endpoint: API endpoint to request.
            payload: Request payload (will be converted to JSON).

        Returns:
            The JSON response as a dictionary.

        Raises:
            LegifranceError: For Legifrance-specific errors
            AuthenticationError: If authentication fails
            DataParsingError: If the response cannot be parsed as JSON
            APIError: For other API-related errors
        """
        # Ensure headers are set correctly
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            }
        )

        # Use the request method which now has proper error handling
        return self.request("POST", endpoint, payload=payload)
