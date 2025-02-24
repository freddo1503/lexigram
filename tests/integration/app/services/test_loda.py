from datetime import date

from app.models import loda
from app.models.loda import DateRange
from app.services.loda import fetch_loda_list


def test_fetch_loda_list_integration(api_client):
    """Integration test for fetch_loda_list function."""

    request_payload = loda.RequestPayload(
        sort="PUBLICATION_DATE_ASC",
        legalStatus=["VIGUEUR", "ABROGE", "VIGUEUR_DIFF"],
        pageNumber=1,
        natures=["LOI", "ORDONNANCE", "DECRET"],
        secondSort="PUBLICATION_DATE_ASC",
        signatureDate=DateRange(start=date(2016, 1, 1), end=date(2016, 12, 31)),
        pageSize=10,
        publicationDate=DateRange(start=date(2016, 1, 1), end=date(2016, 12, 31)),
    )

    loda_list = fetch_loda_list(api_client=api_client, payload=request_payload)

    assert isinstance(loda_list, loda.ResponsePayload)
    assert isinstance(loda_list.executionTime, int)
    assert isinstance(loda_list.results, list)

    if loda_list.results:
        assert isinstance(loda_list.results[0], loda.ResultItem)
        assert isinstance(loda_list.results[0].id, str)
        assert isinstance(loda_list.results[0].titre, str)
