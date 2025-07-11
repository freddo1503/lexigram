def test_ping_endpoint(api_client):
    """
    Integration test for the ping endpoint. It verifies that the /consult/ping endpoint returns 'pong'.
    """
    api_client.session.headers.update({"Accept": "text/plain"})

    response = api_client.get("/consult/ping")

    # PyLegifrance client returns Response object, need to get text
    assert response.text == "pong", f"Unexpected response: {response.text}"
