import time
from datetime import date

from app.api_client import LegifranceApiClient
from app.models import consult, loda
from app.models.loda import DateRange
from app.services.legifrance import fetch_legi_consult, fetch_loda_list


def _try_fetch_details(api_client: LegifranceApiClient, law, index):
    """
    Attempt to fetch details for a given law and return the details if valid.
    """
    try:
        details = fetch_legi_consult(
            api_client=api_client,
            payload=consult.LegiConsultRequest(
                date=law.lastUpdate,
                textId=law.id,
            ),
        )
        if getattr(details, "title", None) and getattr(details, "articles", []):
            return details
    except Exception as e:
        print(f"Error fetching details for result index {index}: {e}")
    return None


def fetch_latest_law(api_client: LegifranceApiClient):
    """
    Fetch the latest law that contains valid details.
    """
    lodal_list = fetch_loda_list(
        api_client=api_client,
        payload=loda.RequestPayload(
            sort="PUBLICATION_DATE_DESC",
            legalStatus=["VIGUEUR"],
            pageNumber=1,
            natures=["LOI"],
            secondSort="PUBLICATION_DATE_DESC",
            pageSize=10,
            publicationDate=DateRange(
                start=date(date.today().year, 1, 1),
                end=date(date.today().year, 12, 31),
            ),
        ),
    )

    for idx, law in enumerate(lodal_list.results):
        details = _try_fetch_details(api_client=api_client, law=law, index=idx)
        time.sleep(1)
        if details:  # Only return the first valid law
            return details.model_dump(mode="json")
        print(f"Skipping law at index {idx}: No valid details found.")

    # No valid law found
    return {
        "titre": "",
        "content": "Aucun détail valide n'a été trouvé pour les lois récentes.",
    }
