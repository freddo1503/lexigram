import os

import pytest
from dotenv import load_dotenv

from app.api_client import APIClient

load_dotenv()


@pytest.mark.integration
def test_ping_endpoint():
    """
    Integration test for the ping endpoint. It verifies that the /consult/ping endpoint returns 'pong'.
    """
    base_url = os.environ["BASE_URL"]

    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    token_url = os.environ["TOKEN_URL"]
    client = APIClient(
        base_url=base_url,
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
    )

    client = APIClient(base_url=base_url, token=client.token)

    client.session.headers.update({"Accept": "text/plain"})

    response = client.get("/consult/ping")

    assert response == "pong", f"Unexpected response: {response}"
