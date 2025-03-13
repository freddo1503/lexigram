import logging

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_law_to_dynamodb(
    table_name: str, text_id: str, date: str, is_processed: bool = False
):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    item = {
        "textId": text_id,
        "date": date,
        "isProcessed": is_processed,
    }

    try:
        table.put_item(Item=item)
        return True
    except ClientError as e:
        logger.error(
            f"Error adding item to DynamoDB table: {e.response['Error']['Message']}"
        )
        return False


def get_law_from_dynamodb(table_name: str, text_id: str):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        response = table.get_item(Key={"textId": text_id})
        item = response.get("Item")
        if item:
            return item
        else:
            logger.warning(
                f"Item with textId '{text_id}' not found in table '{table_name}'."
            )
            return None
    except ClientError as e:
        logger.error(
            f"Error retrieving item from DynamoDB table: {e.response['Error']['Message']}"
        )
        return None


def update_law_in_dynamodb(table_name: str, text_id: str, updates: dict):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    expression = "SET " + ", ".join([f"{key} = :{key}" for key in updates.keys()])
    expression_values = {f":{k}": v for k, v in updates.items()}

    try:
        table.update_item(
            Key={"textId": text_id},
            UpdateExpression=expression,
            ExpressionAttributeValues=expression_values,
        )
        return True
    except ClientError as e:
        logger.error(
            f"Error updating item in DynamoDB table: {e.response['Error']['Message']}"
        )
        return False


def delete_law_from_dynamodb(table_name: str, text_id: str):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        table.delete_item(Key={"textId": text_id})
        return True
    except ClientError as e:
        logger.error(
            f"Error deleting item from DynamoDB table: {e.response['Error']['Message']}"
        )
        return False
