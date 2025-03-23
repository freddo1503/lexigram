import json
import os
from datetime import date

from app import config
from app.agents.crew import create_crew
from app.config import api_client
from app.models import consult, loda
from app.models.consult import LegiConsultResponse
from app.services.dynamo_utils import DynamoDBClient
from app.services.legifrance import fetch_legi_consult
from app.services.publisher import Publisher
from infra.dynamo_db_table import LawPostSchema

os.environ["OTEL_SDK_DISABLED"] = "true"  # Disable OpenTelemetry SDK


def main():
    """
    Main function to synchronize, process, and publish laws on Instagram.

    Workflow Steps:
    1. Synchronize the DynamoDB table with the latest laws.
    2. Retrieve the textId and date of the oldest unprocessed law.
    3. Fetch the corresponding law details and handle them with the crew.
    4. Generate an image and caption, and publish it to Instagram.
    5. Mark the law as processed in the DynamoDB table.
    """
    dynamo_client = init_dynamo_client()

    # Step 1: Sync DynamoDB with the latest laws from the API
    sync_dynamodb_with_latest_laws(dynamo_client)

    # Step 2: Retrieve the oldest unprocessed law
    last_unprocessed_law = dynamo_client.get_last_unprocessed_law()

    # Step 3: Fetch law details from Legifrance
    law_details = fetch_law_details_from_legifrance(last_unprocessed_law)

    # Step 4: Process and publish the law using the crew
    process_and_publish_law(dynamo_client, last_unprocessed_law, law_details)


def init_dynamo_client():
    """
    Initialize the DynamoDB client with the appropriate table schema.
    """
    return DynamoDBClient(LawPostSchema().table_name)


def sync_dynamodb_with_latest_laws(dynamo_client):
    """
    Synchronize the DynamoDB table with the latest laws available online.
    """
    current_year = date.today().year
    print("Synchronizing DynamoDB with the latest law entries...")
    dynamo_client.sync_new_loda_entries_to_dynamodb(
        api_client=api_client,
        payload=loda.RequestPayload(
            sort="PUBLICATION_DATE_DESC",
            legalStatus=["VIGUEUR"],
            pageNumber=1,
            natures=["LOI"],
            secondSort="PUBLICATION_DATE_DESC",
            pageSize=10,
            publicationDate=loda.DateRange(
                start=date(current_year, 1, 1),
                end=date(current_year, 12, 31),
            ),
        ),
    )
    print("Synchronization complete.")


def fetch_law_details_from_legifrance(last_law) -> LegiConsultResponse:
    """
    Use Legifrance API to fetch law details based on the textId and date.

    Parameters:
        last_law (dict): Information of the last unprocessed law.

    Returns:
        Object containing the fetched law details.
    """
    print("Fetching law details from Legifrance...")
    return fetch_legi_consult(
        api_client=api_client,
        payload=consult.LegiConsultRequest(
            date=last_law["date"], textId=last_law["textId"]
        ),
    )


def process_and_publish_law(dynamo_client, last_law, law_details: LegiConsultResponse):
    """
    Process the law details with the crew, generate content, and publish it to Instagram.

    Parameters:
        dynamo_client (DynamoDBClient): DynamoDB client object.
        last_law (dict): Information of the last unprocessed law.
        law_details (object): Details of the law fetched from Legifrance.
    """
    print("Initializing the crew for content processing...")
    crew = create_crew()

    # Pass law details to the crew for processing
    resume = crew.kickoff(
        inputs={
            "titre": law_details.title,
            "date_publication": law_details.dateParution,
            "signataires": law_details.signers,
            "contenu": law_details.articles[0].content,
        }
    )

    # Extract generated content
    image_generation = json.loads(resume.tasks_output[1].raw)
    caption = resume.tasks_output[2].raw

    try:
        print("Publishing content to Instagram...")
        publisher = Publisher(access_token=config.access_token)

        # Publish the content
        published_id = publisher.publish(
            image_url=image_generation["image_url"], caption=caption
        )
        print(f"Successfully published to Instagram with ID: {published_id}")

        if published_id:
            # Mark the law as processed
            update_processed_law_status(dynamo_client, last_law)
    except Exception as error:
        print(f"Error publishing to Instagram: {error}")


def update_processed_law_status(dynamo_client, law):
    """
    Update the status of a processed law in the DynamoDB table.

    Parameters:
        dynamo_client (DynamoDBClient): DynamoDB client object.
        law (dict): Information of the law being marked as processed.
    """
    key = {"textId": law["textId"]}
    updates = {"isProcessed": True}
    dynamo_client.update_item(key=key, updates=updates)
    print("Law status updated to 'processed' in DynamoDB.")


# Ensure the script runs directly
if __name__ == "__main__":
    main()
