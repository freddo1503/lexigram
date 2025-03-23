from datetime import date, datetime

from app.models import loda
from app.services.legifrance import fetch_loda_list


def create_item(
    text_id: str, timestamp: datetime = None, is_processed: bool = False
) -> dict:
    """Helper function to create a DynamoDB item."""
    ts = (timestamp or datetime.utcnow()).isoformat()
    return {"textId": text_id, "date": ts, "isProcessed": is_processed}


def test_sync_new_loda_entries_to_dynamodb(api_client, dynamodb_client, dynamo_table):
    request_payload = loda.RequestPayload(
        sort="PUBLICATION_DATE_DESC",
        legalStatus=["VIGUEUR"],
        pageNumber=1,
        natures=["LOI"],
        secondSort="PUBLICATION_DATE_DESC",
        signatureDate=loda.DateRange(start=date(2024, 1, 1), end=date(2024, 2, 28)),
        pageSize=5,
    )
    loda_response = None
    try:
        dynamodb_client.sync_new_loda_entries_to_dynamodb(
            api_client=api_client, payload=request_payload
        )
        loda_response = fetch_loda_list(api_client=api_client, payload=request_payload)

        for law in loda_response.results:
            dynamo_response = dynamo_table.get_item(Key={"textId": law.id})
            assert "Item" in dynamo_response, (
                f"Law with textId {law.id} not found in DynamoDB"
            )
            item = dynamo_response["Item"]
            assert item["textId"] == law.id
    finally:
        if loda_response:
            for law in loda_response.results:
                dynamo_table.delete_item(Key={"textId": law.id})


def test_put_item(dynamodb_client, dynamo_table):
    text_id = "test-id-put"
    item = create_item(text_id)
    try:
        dynamodb_client.put_item(item)
        response = dynamo_table.get_item(Key={"textId": text_id})

        assert "Item" in response, f"Item with textId {text_id} not found in table"
        assert response["Item"] == item
    finally:
        dynamo_table.delete_item(Key={"textId": text_id})


def test_get_item(dynamodb_client, dynamo_table):
    text_id = "test-id-get"
    item = create_item(text_id)
    try:
        dynamo_table.put_item(Item=item)
        retrieved_item = dynamodb_client.get_item(key={"textId": text_id})

        assert retrieved_item == item, "Retrieved item does not match the original"
    finally:
        dynamo_table.delete_item(Key={"textId": text_id})


def test_update_item(dynamodb_client, dynamo_table):
    text_id = "test-id-update"
    item = create_item(text_id)
    try:
        # Insert the initial item into the mock table
        dynamo_table.put_item(Item=item)

        # Define the update parameters
        key = {"textId": text_id}
        updates = {"isProcessed": True}

        # Call the update_item method with the correct arguments
        result = dynamodb_client.update_item(key=key, updates=updates)

        # Assert that the update operation was successful
        assert result is True, "Update operation did not return True"

        # Retrieve the item and verify the updates
        response = dynamo_table.get_item(Key=key)
        updated_item = response.get("Item", {})

        assert updated_item.get("isProcessed") is True, "Update operation failed"
    finally:
        # Cleanup: Delete the test item
        dynamo_table.delete_item(Key={"textId": text_id})


def test_delete_item(dynamodb_client, dynamo_table):
    text_id = "test-id-delete"
    item = create_item(text_id)
    dynamo_table.put_item(Item=item)

    dynamodb_client.delete_item(key={"textId": text_id})

    response = dynamo_table.get_item(Key={"textId": text_id})

    assert "Item" not in response, f"Item with textId {text_id} was not deleted"
