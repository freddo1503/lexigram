import logging

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

    def update_item(self, key: dict, updates: dict):
        expression = "SET " + ", ".join([f"{key} = :{key}" for key in updates.keys()])
        expression_values = {f":{k}": v for k, v in updates.items()}

        try:
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
        if existing_item:
            return

        item = {"textId": text_id, "date": date, "isProcessed": False}
        self.put_item(item)

    def sync_new_loda_entries_to_dynamodb(
        self, api_client, payload: loda.RequestPayload
    ):
        """
        Synchronizes multiple LODA entries to DynamoDB.
        """
        loda_response = fetch_loda_list(api_client, payload)

        for law in loda_response.results:
            self.sync_new_law_to_dynamodb(law)

        return "Synchronization complete"

    def get_last_unprocessed_law(self):
        """
        Retrieves the latest unprocessed law entry (`isProcessed=false`) from DynamoDB.
        Returns `textId` and `date` of the law.
        """
        try:
            response = self.table.scan(
                FilterExpression=Attr("isProcessed").eq(
                    False
                ),  # Filter for unprocessed entries
                ProjectionExpression="textId, date",  # Fetch only `textId` and `date`
            )
            items = response.get("Items", [])
            if items:
                # Assuming latest entries have the highest `date`
                last_unprocessed = sorted(items, key=lambda x: x["date"], reverse=True)[
                    0
                ]
                return last_unprocessed
            return None  # Return None if no unprocessed laws
        except ClientError as e:
            logger.error(
                f"Error retrieving last unprocessed law: {e.response['Error']['Message']}"
            )
            return None
