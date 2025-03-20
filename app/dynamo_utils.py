import logging

import boto3
from botocore.exceptions import ClientError

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
