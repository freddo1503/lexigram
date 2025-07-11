from app.services.law_processing_service import LawProcessingService
from app.services.law_sync_service import LawSyncService


def test_services_can_be_initialized(api_client, dynamodb_client):
    """Test that all services can be initialized without errors."""

    law_sync_service = LawSyncService(dynamodb_client)
    assert law_sync_service is not None
    assert law_sync_service.dynamo_client == dynamodb_client

    law_processing_service = LawProcessingService(dynamodb_client)
    assert law_processing_service is not None
    assert law_processing_service.dynamo_client == dynamodb_client


def test_sync_service_runs(api_client, dynamodb_client):
    """Test that sync service can run without errors."""

    law_sync_service = LawSyncService(dynamodb_client)
    result = law_sync_service.sync_laws_for_year()
    assert isinstance(result, int)
    assert result >= 0


def test_processing_service_gets_next_law(api_client, dynamodb_client):
    """Test that processing service can get next law."""

    law_processing_service = LawProcessingService(dynamodb_client)
    next_law = law_processing_service.get_next_unprocessed_law()

    # Should return None or dict - both are valid
    assert next_law is None or isinstance(next_law, dict)
