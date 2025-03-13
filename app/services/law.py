import boto3
from botocore.exceptions import ClientError


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
        print(f"Successfully added item to table '{table_name}': {item}")
        return True
    except ClientError as e:
        print(f"Error adding item to DynamoDB table: {e.response['Error']['Message']}")
        return False


def get_law_from_dynamodb(table_name: str, text_id: str):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        response = table.get_item(Key={"textId": text_id})
        item = response.get("Item")
        if item:
            print(f"Successfully retrieved item: {item}")
            return item
        else:
            print(f"Item with textId '{text_id}' not found in table '{table_name}'.")
            return None
    except ClientError as e:
        print(
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
        print(
            f"Successfully updated item with textId '{text_id}' in table '{table_name}'."
        )
        return True
    except ClientError as e:
        print(
            f"Error updating item in DynamoDB table: {e.response['Error']['Message']}"
        )
        return False


def delete_law_from_dynamodb(table_name: str, text_id: str):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        table.delete_item(Key={"textId": text_id})
        print(
            f"Successfully deleted item with textId '{text_id}' from table '{table_name}'."
        )
        return True
    except ClientError as e:
        print(
            f"Error deleting item from DynamoDB table: {e.response['Error']['Message']}"
        )
        return False
