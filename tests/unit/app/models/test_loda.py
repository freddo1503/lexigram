import json

from app.models.loda import RequestPayload


def test_request_payload_serialization():
    payload_data = {
        "sort": "PUBLICATION_DATE_ASC",
        "legalStatus": ["VIGUEUR", "ABROGE", "VIGUEUR_DIFF"],
        "pageNumber": 1,
        "natures": ["LOI", "ORDONNANCE", "DECRET"],
        "secondSort": "PUBLICATION_DATE_ASC",
        "signatureDate": {"start": "2016-01-01", "end": "2016-12-31"},
        "pageSize": 10,
        "publicationDate": {"start": "2016-01-01", "end": "2016-12-31"},
    }

    request_payload = RequestPayload(**payload_data)
    json_data = json.loads(request_payload.model_dump_json())
    assert json_data == payload_data
