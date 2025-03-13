from app.services.law import add_law_to_dynamodb, get_law_from_dynamodb
from app.services.legifrance import fetch_loda_list
from infra.dynamo_db_table import LawPostSchema


def sync_new_loda_entries_to_dynamodb(api_client, payload):
    """
    Synchronizes new LODA entries to DynamoDB with only necessary fields.

    Args:
        api_client (APIClient): Instance of the API client for making requests.
        payload (loda.RequestPayload): Request payload specifying filters for LODA data.

    Returns:
        dict: Summary of the synchronization results
              (e.g., number of items synced, skipped, errors encountered).
    """
    # Fetch the list of results
    loda_response = fetch_loda_list(api_client, payload)

    # Initialize the table name
    table_name = LawPostSchema().table_name

    # Synchronization statistics
    sync_stats = {"synced": 0, "skipped": 0, "errors": 0}

    # Iterate over each result in the response
    for law in loda_response.results:
        text_id = law.id
        date = law.lastUpdate.isoformat() if law.lastUpdate else None

        existing_item = get_law_from_dynamodb(table_name, text_id)

        if existing_item:
            sync_stats["skipped"] += 1
            continue

        is_processed = False

        if add_law_to_dynamodb(table_name, text_id, date, is_processed):
            sync_stats["synced"] += 1
        else:
            sync_stats["errors"] += 1

    return sync_stats
