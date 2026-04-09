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

    def get_item(self, key: t.Dict[str, t.Any]) -> t.Optional[t.Dict[str, t.Any]]:
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            logger.error("Error fetching item: %s", e.response["Error"]["Message"])
            return None

    def put_item(self, item: t.Dict[str, t.Any]) -> bool:
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error("Error adding item: %s", e.response["Error"]["Message"])
            return False

    def update_item(self, key: t.Dict[str, t.Any], updates: t.Dict[str, t.Any]) -> bool:
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
            logger.error("Error updating item: %s", e.response["Error"]["Message"])
            return False

    def delete_item(self, key: t.Dict[str, t.Any]) -> bool:
        try:
            self.table.delete_item(Key=key)
            return True
        except ClientError as e:
            logger.error("Error deleting item: %s", e.response["Error"]["Message"])
            return False

    def scan(
        self, filter_expression: t.Any, expression_values: t.Dict[str, t.Any]
    ) -> t.List[t.Dict[str, t.Any]]:
        try:
            response = self.table.scan(
                FilterExpression=filter_expression,
                ExpressionAttributeValues=expression_values,
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("Error scanning table: %s", e.response["Error"]["Message"])
            return []

    def sync_new_law_to_dynamodb(self, text_loda) -> bool:
        """
        Syncs one TextLoda object to DynamoDB.
        Stores textId, date, nature, and isProcessed.

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
        if existing_item:
            logger.debug("Law already exists: %s", law_id)
            return False

        # Extract date from the TextLoda ID (format: LEGITEXT000051827204_02-07-2025)
        date_part = law_id.split("_")[1] if "_" in law_id else None

        # The outer TexteLoda wrapper in pylegifrance/fonds/loda.py does not
        # expose .nature directly; reach through to the inner pydantic model
        # which publicly declares `nature` as a property.
        # TODO: use text_loda.nature once pylegifrance exposes it on the wrapper.
        nature = text_loda._texte.nature if text_loda._texte else None

        item = {
            "textId": law_id,
            "date": date_part,
            "isProcessed": False,
            "nature": nature,
        }
        self.put_item(item)
        logger.debug("Added new law: %s (%s)", law_id, nature)
        return True

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

        logger.info("Synchronized %d new laws successfully.", sync_count)
        return f"Synchronization complete: {sync_count} new laws added."

    def get_oldest_unprocessed_law(self) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Retrieves the oldest unprocessed law entry (`isProcessed=false`) from DynamoDB.
        Returns a dictionary with `textId`, `date`, and `nature` of the law.
        Example format:
        {'date': '02-07-2025', 'textId': 'LEGITEXT000051827204_02-07-2025', 'nature': 'LOI'}
        """
        try:
            response = self.table.scan(
                FilterExpression=Attr("isProcessed").eq(False),
                ProjectionExpression="#textId, #date, #nature",
                ExpressionAttributeNames={
                    "#textId": "textId",
                    "#date": "date",
                    "#nature": "nature",
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
                "nature": oldest_unprocessed.get("nature"),
            }
            return result
        except ClientError as e:
            logger.error(
                "Error retrieving oldest unprocessed law: %s",
                e.response["Error"]["Message"],
            )
            return None
