import typing as t

import pytest
import requests

from app.api_client import LegifranceApiClient

CLIENT_ID = "dummy_client_id"
CLIENT_SECRET = "dummy_client_secret"
TOKEN_URL = "http://dummy.token.url"


class DummyResponse:
    def __init__(
        self, json_data: t.Dict[str, t.Any], text: str, raise_error: bool = False
    ):
        self._json_data = json_data
        self.text = text
        self.raise_error = raise_error

    def json(self) -> t.Dict[str, t.Any]:
        if self.raise_error:
            raise ValueError("Invalid JSON")
        return self._json_data


def dummy_post_success(
    url: str, data: t.Dict[str, t.Any], headers: t.Dict[str, str]
) -> DummyResponse:
    return DummyResponse(
        {"access_token": "dummy_token", "expires_in": 3600}, "dummy response"
    )


def dummy_post_json_error(
    url: str, data: t.Dict[str, t.Any], headers: t.Dict[str, str]
) -> DummyResponse:
    return DummyResponse({}, "error response", raise_error=True)


def test_get_access_token_success(monkeypatch):
    monkeypatch.setattr(requests, "post", dummy_post_success)
    client = LegifranceApiClient(
        base_url="http://dummy.api",
        token=None,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_url=TOKEN_URL,
    )
    assert client.token == "dummy_token"


def test_get_access_token_json_error(monkeypatch):
    monkeypatch.setattr(requests, "post", dummy_post_json_error)
    with pytest.raises(ValueError):
        LegifranceApiClient(
            base_url="http://dummy.api",
            token=None,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_url=TOKEN_URL,
        )
