import uuid

import pytest

from app.dynamo_utils import DynamoDBClient
from infra.dynamo_db_table import LawPostSchema

client = DynamoDBClient(LawPostSchema().table_name)


@pytest.fixture(scope="function")
def law_data():
    """
    Fixture to provide a unique law data payload.
    """
    unique_text_id = f"test-law-{uuid.uuid4().hex}"
    return {
        "textId": unique_text_id,
        "date": "2023-07-01",
        "isProcessed": False,
    }


@pytest.fixture(scope="function")
def clean_up(law_data):
    """
    Fixture to clean up the DynamoDB table after each test by deleting the test law data.
    """
    yield
    client.delete_item(key={"textId": law_data["textId"]})


def test_add_law(law_data, clean_up):
    """
    Test for adding a law to DynamoDB.
    """
    result = client.put_item(law_data)
    assert result is True, "Failed to add law item to DynamoDB."


def test_get_law(law_data, clean_up):
    """
    Test for fetching a law from DynamoDB.
    """
    client.put_item(law_data)

    item = client.get_item(key={"textId": law_data["textId"]})
    assert item is not None, "Law item was not found in DynamoDB."
    assert item["textId"] == law_data["textId"]
    assert item["date"] == law_data["date"]
    assert item["isProcessed"] == law_data["isProcessed"]


def test_update_law(law_data, clean_up):
    """
    Test for updating a law in DynamoDB.
    """
    client.put_item(law_data)

    updates = {"isProcessed": True}
    result = client.update_item(key={"textId": law_data["textId"]}, updates=updates)
    assert result is True, "Failed to update law item in DynamoDB."

    item = client.get_item(key={"textId": law_data["textId"]})
    assert item is not None, "Law item not found after update."
    assert item["isProcessed"] is True, "Law item was not updated correctly."


def test_delete_law(law_data):
    """
    Test for deleting a law from DynamoDB.
    """
    client.put_item(law_data)

    result = client.delete_item(key={"textId": law_data["textId"]})
    assert result is True, "Failed to delete law item from DynamoDB."

    item = client.get_item(key={"textId": law_data["textId"]})
    assert item is None, "Law item still exists in DynamoDB after deletion."
