from dynamo_utils import DynamoDBClient

from app.services.legifrance import fetch_loda_list
from infra.dynamo_db_table import LawPostSchema


def sync_law_to_dynamodb(client: DynamoDBClient, law, sync_stats):
    """
    Syncs one law entry to DynamoDB, updating the synchronization stats.
    """
    text_id = law.id
    date = law.lastUpdate.isoformat() if law.lastUpdate else None

    existing_item = client.get_item(key={"textId": text_id})
    if existing_item:
        sync_stats["skipped"] += 1
        return

    item = {"textId": text_id, "date": date, "isProcessed": False}
    if client.put_item(item):
        sync_stats["synced"] += 1
    else:
        sync_stats["errors"] += 1


def sync_new_loda_entries_to_dynamodb(api_client, payload):
    loda_response = fetch_loda_list(api_client, payload)
    client = DynamoDBClient(LawPostSchema().table_name)
    sync_stats = {"synced": 0, "skipped": 0, "errors": 0}

    for law in loda_response.results:
        sync_law_to_dynamodb(client, law, sync_stats)

    return sync_stats
