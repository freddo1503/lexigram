import uuid

import pytest

from app.services.law import (
    add_law_to_dynamodb,
    delete_law_from_dynamodb,
    get_law_from_dynamodb,
    update_law_in_dynamodb,
)
from infra.dynamo_db_table import LawPostSchema


@pytest.fixture(scope="function")
def table_name():
    table_name = LawPostSchema().table_name
    return table_name


@pytest.fixture(scope="function")
def law_data():
    unique_text_id = f"test-law-{uuid.uuid4().hex}"
    return {
        "textId": unique_text_id,
        "date": "2023-07-01",
        "isProcessed": False,
    }


@pytest.fixture(scope="function")
def clean_up(table_name, law_data):
    yield
    delete_law_from_dynamodb(table_name, law_data["textId"])


def test_add_law(law_data, table_name, clean_up):
    result = add_law_to_dynamodb(
        table_name, law_data["textId"], law_data["date"], law_data["isProcessed"]
    )
    assert result is True, "Failed to add law item to DynamoDB."


def test_get_law(law_data, table_name, clean_up):
    add_law_to_dynamodb(
        table_name, law_data["textId"], law_data["date"], law_data["isProcessed"]
    )

    item = get_law_from_dynamodb(table_name, law_data["textId"])
    assert item is not None, "Law item was not found in DynamoDB."
    assert item["textId"] == law_data["textId"]
    assert item["date"] == law_data["date"]
    assert item["isProcessed"] == law_data["isProcessed"]


def test_update_law(law_data, table_name, clean_up):
    add_law_to_dynamodb(
        table_name, law_data["textId"], law_data["date"], law_data["isProcessed"]
    )

    updates = {"isProcessed": "true"}
    result = update_law_in_dynamodb(table_name, law_data["textId"], updates)
    assert result is True, "Failed to update law item in DynamoDB."

    item = get_law_from_dynamodb(table_name, law_data["textId"])
    assert item is not None, "Law item not found after update."
    assert item["isProcessed"] == "true", "Law item was not updated correctly."


def test_delete_law(law_data, table_name):
    add_law_to_dynamodb(
        table_name, law_data["textId"], law_data["date"], law_data["isProcessed"]
    )

    result = delete_law_from_dynamodb(table_name, law_data["textId"])
    assert result is True, "Failed to delete law item from DynamoDB."

    item = get_law_from_dynamodb(table_name, law_data["textId"])
    assert item is None, "Law item still exists in DynamoDB after deletion."
