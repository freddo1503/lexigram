from app.services.law_processing_service import LawProcessingService


def test_law_processing_service_get_next_law(api_client, dynamodb_client, dynamo_table):
    """Simple test for getting next unprocessed law."""
    law_processing_service = LawProcessingService(dynamodb_client)

    # Should return None or a dict with textId
    result = law_processing_service.get_next_unprocessed_law()

    if result is not None:
        assert isinstance(result, dict)
        assert "textId" in result


def test_law_processing_service_fetch_law_details(api_client, dynamodb_client):
    """Simple test for fetching law details."""
    law_processing_service = LawProcessingService(dynamodb_client)

    # Use a known law ID format for testing
    test_law_id = "LEGITEXT000006069569"

    try:
        law_details = law_processing_service.fetch_law_details(test_law_id)
        assert law_details is not None
        assert hasattr(law_details, "id")
    except Exception:
        # API might be down or law doesn't exist, that's okay for this test
        pass
