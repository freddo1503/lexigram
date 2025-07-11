import logging
import typing as t

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# Removed imports for deleted modules - using PyLegifrance now

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

    def sync_new_law_to_dynamodb(self, text_loda) -> bool:
        """
        Syncs one TextLoda object to DynamoDB.
        Stores textId (from text_loda.id), date (extracted from id), and isProcessed.

        Args:
            text_loda: PyLegifrance TextLoda object

        Returns:
            bool: True if new law was added, False if it already existed
        """
        law_id = text_loda.id
        if not law_id:
            logger.warning("TextLoda missing id, skipping")
            return False

        existing_item = self.get_item(key={"textId": law_id})
        if not existing_item:
            # Extract date from the TextLoda ID (format: LEGITEXT000051827204_02-07-2025)
            date_part = None
            if "_" in law_id:
                date_part = law_id.split("_")[1]

            item = {"textId": law_id, "date": date_part, "isProcessed": False}
            self.put_item(item)
            logger.debug(f"Added new law: {law_id}")
            return True
        else:
            logger.debug(f"Law already exists: {law_id}")
            return False

    def sync_new_entries_to_dynamodb(self, text_lodas: t.List) -> str:
        """
        Synchronizes multiple TextLoda objects to DynamoDB.

        Args:
            text_lodas: List of PyLegifrance TextLoda objects

        Returns:
            str: Summary message of synchronization results
        """
        logger.info("Starting law entries synchronization...")
        sync_count = 0

        for text_loda in text_lodas:
            if self.sync_new_law_to_dynamodb(text_loda):
                sync_count += 1

        logger.info(f"Synchronized {sync_count} new laws successfully.")
        return f"Synchronization complete: {sync_count} new laws added."

    def get_last_unprocessed_law(self) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Retrieves the latest unprocessed law entry (`isProcessed=false`) from DynamoDB.
        Returns a dictionary with `textId` and `date` of the law.
        Example format:
        {'date': '02-07-2025', 'textId': 'LEGITEXT000051827204_02-07-2025'}
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

            # Sort by date if available, otherwise by textId
            if items[0].get("date"):
                oldest_unprocessed = sorted(items, key=lambda x: x.get("date", ""))[0]
            else:
                oldest_unprocessed = items[0]

            result = {
                "textId": oldest_unprocessed.get("textId"),
                "date": oldest_unprocessed.get("date"),
            }
            return result
        except ClientError as e:
            logger.error(
                f"Error retrieving last unprocessed law: {e.response['Error']['Message']}"
            )
            return None
