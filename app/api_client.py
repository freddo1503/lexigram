import logging
import time
import typing as t

import requests

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

    def _get_access_token(self) -> str:
        """
        Retrieves an access token using client credentials and updates the token expiry.

        Returns:
            str: A valid access token.
        """
        payload: t.Dict[str, t.Any] = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": "openid",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(self._token_url, data=payload, headers=headers)
        try:
            token_data = response.json()
        except ValueError as err:
            logger.error("Failed to parse token response as JSON: %s", err)
            raise

        if (
            not token_data.get("access_token")
            or token_data.get("access_token") == "null"
        ):
            logger.error("Failed to obtain access token. Response: %s", response.text)
            raise RuntimeError("Failed to obtain access token.")

        # Cache the token expiry; subtract a safety margin (e.g., 60 seconds)
        expires_in = token_data.get("expires_in", 3600)
        self.token_expiry = time.time() + expires_in - 60
        return token_data.get("access_token")

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

    def request(
        self,
        method: str,
        endpoint: str,
        payload: t.Optional[str] = None,
        params: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> requests.Response:
        """
        Send an HTTP request and return the JSON response.
        """
        self._ensure_token()  # Refresh token if necessary
        url = self._build_url(endpoint)
        response = self.session.request(method, url, json=payload, params=params)
        try:
            response.raise_for_status()
        except requests.HTTPError as http_err:
            logger.error("HTTP error occurred: %s", http_err)
            raise
        except Exception as err:
            logger.error("Unexpected error occurred: %s", err)
            raise

        return response.json()

    def get(
        self,
        endpoint: str,
        params: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> str:
        """
        Perform a GET request and return the response as a string.

        Args:
            endpoint (str): API endpoint to request.
            params (Optional[Dict[str, Any]]): Query parameters.

        Returns:
            str: The response content as a string.
        """
        self._ensure_token()  # Refresh token if necessary
        url = self._build_url(endpoint)
        response = self.session.get(url, params=params)

        try:
            return response.json()
        except requests.JSONDecodeError:
            return response.text

    def post(
        self,
        endpoint: str,
        payload: t.Optional[str] = None,
    ) -> requests.Response:
        """
        Perform a POST request.
        """
        self.session.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        return self.request("POST", endpoint, payload=payload)
