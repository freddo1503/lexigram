import logging
import typing as t
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from app.models import loda
from app.services.legifrance import fetch_loda_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DynamoDBClient:
    def __init__(self, table_name: str):
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(table_name)

    def get_item(self, key: dict):
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Error fetching item: {e.response['Error']['Message']}")
            return None

    def put_item(self, item: dict):
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Error adding item: {e.response['Error']['Message']}")
            return False

    def update_item(self, key: dict, updates: dict) -> bool:
        try:
            expression = "SET " + ", ".join(f"{k} = :{k}" for k in updates)
            expression_values = {f":{k}": v for k, v in updates.items()}

            self.table.update_item(
                Key=key,
                UpdateExpression=expression,
                ExpressionAttributeValues=expression_values,
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating item: {e.response['Error']['Message']}")
            return False

    def delete_item(self, key: dict):
        try:
            self.table.delete_item(Key=key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting item: {e.response['Error']['Message']}")
            return False

    def scan(self, filter_expression, expression_values):
        try:
            response = self.table.scan(
                FilterExpression=filter_expression,
                ExpressionAttributeValues=expression_values,
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Error scanning table: {e.response['Error']['Message']}")
            return []

    def sync_new_law_to_dynamodb(self, law):
        """
        Syncs one law entry to DynamoDB.
        """
        text_id = law.id
        date = law.lastUpdate.isoformat() if law.lastUpdate else None

        existing_item = self.get_item(key={"textId": text_id})
        if not existing_item:
            item = {"textId": text_id, "date": date, "isProcessed": False}
            self.put_item(item)
            return
        else:
            return False

    def sync_new_loda_entries_to_dynamodb(
        self, api_client, payload: loda.RequestPayload
    ):
        """
        Synchronizes multiple LODA entries to DynamoDB.
        """
        logger.info("Starting LODA entries synchronization...")
        loda_response = fetch_loda_list(api_client, payload)

        sync_count = 0

        for law in loda_response.results:
            if self.sync_new_law_to_dynamodb(law):
                sync_count += 1

        logger.info(f"Synchronized {sync_count} new laws successfully.")
        return f"Synchronization complete: {sync_count} new laws added."

    def get_last_unprocessed_law(self) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Retrieves the latest unprocessed law entry (`isProcessed=false`) from DynamoDB.
        Returns a dictionary with `textId` and `date` of the law.
        Example format:
        {'date': '2025-03-15T00:00:00+00:00', 'textId': 'LEGITEXT000051331433'}
        """
        try:
            response = self.table.scan(
                FilterExpression=Attr("isProcessed").eq(False),
                ProjectionExpression="#textId, #date",
                ExpressionAttributeNames={
                    "#textId": "textId",
                    "#date": "date",
                },
            )
            items = response.get("Items", [])
            if not items:
                return None

            oldest_unprocessed = sorted(items, key=lambda x: x["date"])[0]

            date_str = oldest_unprocessed.get("date")
            law_date = datetime.fromisoformat(date_str).date() if date_str else None

            result = {
                "date": law_date,
                "textId": oldest_unprocessed.get("textId"),
            }
            return result
        except ClientError as e:
            logger.error(
                f"Error retrieving last unprocessed law: {e.response['Error']['Message']}"
            )
            return None
