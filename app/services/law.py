from app.dynamo_utils import DynamoDBClient
from infra.dynamo_db_table import LawPostSchema

client = DynamoDBClient(LawPostSchema().table_name)


def add_law_to_dynamodb(text_id: str, date: str, is_processed: bool = False):
    item = {
        "textId": text_id,
        "date": date,
        "isProcessed": is_processed,
    }
    return client.put_item(item)


def get_law_from_dynamodb(text_id: str):
    return client.get_item(key={"textId": text_id})


def update_law_in_dynamodb(text_id: str, updates: dict):
    return client.update_item(key={"textId": text_id}, updates=updates)


def delete_law_from_dynamodb(text_id: str):
    return client.delete_item(key={"textId": text_id})
