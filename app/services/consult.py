from app.api_client import APIClient
from app.models.consult import LegiConsultRequest, LegiConsultResponse


def fetch_legi_consult(
    api_client: APIClient, payload: LegiConsultRequest
) -> LegiConsultResponse:
    """Fetch the consultation result for a given legal text."""

    response = api_client.post(
        endpoint="/consult/legiPart",
        payload=payload.model_dump(mode="json", exclude_none=True),
    )

    return LegiConsultResponse.model_validate(response)
