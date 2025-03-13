from datetime import date

import boto3

from app.models import loda
from app.models.loda import DateRange
from app.services.law_tracker import sync_new_loda_entries_to_dynamodb
from app.services.legifrance import fetch_loda_list


def test_sync_new_loda_entries_to_dynamodb(api_client, table_name):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    request_payload = loda.RequestPayload(
        sort="PUBLICATION_DATE_DESC",
        legalStatus=["VIGUEUR"],
        pageNumber=1,
        natures=["LOI"],
        secondSort="PUBLICATION_DATE_DESC",
        signatureDate=DateRange(start=date(2024, 1, 1), end=date(2024, 2, 28)),
        pageSize=5,
    )

    sync_new_loda_entries_to_dynamodb(api_client=api_client, payload=request_payload)

    loda_response = fetch_loda_list(api_client=api_client, payload=request_payload)

    for law in loda_response.results:
        dynamo_response = table.get_item(Key={"textId": law.id})
        assert "Item" in dynamo_response, (
            f"Law with textId {law.id} not found in DynamoDB"
        )

        item = dynamo_response["Item"]
        assert item["textId"] == law.id
