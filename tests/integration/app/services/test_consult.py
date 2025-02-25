import json
from datetime import date

from app.models.consult import LegiConsultRequest
from app.services.consult import fetch_legi_consult


def test_fetch_legi_consult(api_client):
    payload = LegiConsultRequest(
        date=date(2025, 2, 19),
        textId="LEGITEXT000051187583",
    )

    response = fetch_legi_consult(api_client=api_client, payload=payload)

    print(json.dumps(response.model_dump(mode="json"), indent=4))

    assert response.id == "LEGITEXT000051187583_19-02-2025"
