from app.api_client import APIClient
from app.models import loda


def fetch_loda_list(
    api_client: APIClient, payload: loda.RequestPayload
) -> loda.ResponsePayload:
    """Fetch the list of LODA with proper deserialization and error handling."""

    response = api_client.post(
        endpoint="/list/loda", payload=payload.model_dump(mode="json")
    )

    return loda.ResponsePayload.model_validate(response)
