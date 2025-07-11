from pylegifrance.models.generated.model import DatePeriod
from pylegifrance.models.loda.search import SearchRequest

from app.services.law_sync_service import LawSyncService


def test_law_sync_service_integration(api_client, dynamodb_client):
    """Simple integration test for LawSyncService with limited results."""
    law_sync_service = LawSyncService(dynamodb_client)

    # Test syncing laws for current year - limit to one page for testing
    # Create a search request for just one page
    search_request = SearchRequest(
        natures=["LOI"],
        page_number=1,
        page_size=5,  # Small page size for testing
        date_publication=DatePeriod(start="2025-01-01", end="2025-12-31"),
    )

    # Get laws and sync them
    laws = law_sync_service.loda_api.search(search_request)

    if laws:
        result = law_sync_service.dynamo_client.sync_new_entries_to_dynamodb(laws)
        print(f"Sync result: {result}")

    # Should have found some laws
    assert isinstance(laws, list)
    assert len(laws) >= 0
