import typing as t

import pytest
import requests

from app.api_client import LegifranceApiClient
from app.errors.exceptions import DataParsingError

CLIENT_ID = "dummy_client_id"
CLIENT_SECRET = "dummy_client_secret"
TOKEN_URL = "http://dummy.token.url"


class DummyResponse:
    def __init__(
        self,
        json_data: t.Dict[str, t.Any],
        text: str,
        raise_error: bool = False,
        status_code: int = 200,
    ):
        self._json_data = json_data
        self.text = text
        self.raise_error = raise_error
        self.status_code = status_code
        self.url = "http://dummy.url"
        self.request = type("obj", (object,), {"method": "POST"})

    def json(self) -> t.Dict[str, t.Any]:
        if self.raise_error:
            raise ValueError("Invalid JSON")
        return self._json_data

    def raise_for_status(self) -> None:
        """Raises HTTPError if status_code is 4XX or 5XX."""
        if 400 <= self.status_code < 600:
            raise requests.HTTPError(f"HTTP Error: {self.status_code}", response=self)


def dummy_request_success(method: str, url: str, **kwargs: t.Any) -> DummyResponse:
    return DummyResponse(
        {"access_token": "dummy_token", "expires_in": 3600}, "dummy response"
    )


def dummy_request_json_error(method: str, url: str, **kwargs: t.Any) -> DummyResponse:
    return DummyResponse({}, "error response", raise_error=True)


def test_get_access_token_success(monkeypatch):
    monkeypatch.setattr(requests, "request", dummy_request_success)
    client = LegifranceApiClient(
        base_url="http://dummy.api",
        token=None,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_url=TOKEN_URL,
    )
    assert client.token == "dummy_token"


def test_get_access_token_json_error(monkeypatch):
    monkeypatch.setattr(requests, "request", dummy_request_json_error)
    with pytest.raises(DataParsingError):
        LegifranceApiClient(
            base_url="http://dummy.api",
            token=None,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_url=TOKEN_URL,
        )
