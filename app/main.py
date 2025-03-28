import json
import logging
from datetime import date

from bs4 import BeautifulSoup

from app import config
from app.agents.crew import create_crew
from app.config import api_client
from app.models import consult, loda
from app.models.consult import LegiConsultResponse
from app.services.dynamo_utils import DynamoDBClient
from app.services.legifrance import fetch_legi_consult
from app.services.publisher import Publisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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
    return DynamoDBClient(config.DYNAMO_TABLE_NAME)


def sync_dynamodb_with_latest_laws(dynamo_client):
    """
    Synchronize the DynamoDB table with the latest laws available online.
    """
    current_year = date.today().year
    logger.info("Synchronizing DynamoDB with the latest law entries...")
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
    logger.info("Synchronization complete.")


def fetch_law_details_from_legifrance(last_law) -> LegiConsultResponse:
    """
    Use Legifrance API to fetch law details based on the textId and date.

    Parameters:
        last_law (dict): Information of the last unprocessed law.

    Returns:
        Object containing the fetched law details.
    """
    logger.info("Fetching law details from Legifrance...")
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
        law_details (LegiConsultResponse): Details of the law fetched from Legifrance.
    """
    logger.info("Initializing the crew for content processing...")
    crew = create_crew()

    articles = getattr(law_details, "articles", [])
    if not articles or not articles[0]:
        logger.info("No articles available to process.")
        update_processed_law_status(dynamo_client, last_law)
        return

    try:
        logger.info("Combining content from articles...")
        all_contents = "\n\n".join(article.content for article in articles)
        clean_articles = clean_and_format_content(all_contents)
        clean_signataires = clean_and_format_signataires(law_details.signers)

        resume = crew.kickoff(
            inputs={
                "titre": law_details.title,
                "date_publication": law_details.dateParution,
                "signataires": clean_signataires,
                "contenu": clean_articles,
            }
        )

        image_generation = json.loads(resume.tasks_output[1].raw)
        caption = resume.tasks_output[2].raw

        logger.info("Publishing content to Instagram...")
        publisher = Publisher(access_token=config.ACCESS_TOKEN)
        published_id = publisher.publish(
            image_url=image_generation.get("image_url"), caption=caption
        )
        logger.info("Successfully published to Instagram with ID: %s", published_id)

        if published_id:
            update_processed_law_status(dynamo_client, last_law)
    except Exception as error:
        logger.error("Error processing and publishing law: %s", error)


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
    logger.info("Law status updated to 'processed' in DynamoDB.")


def clean_and_format_content(all_contents):
    """
    Clean and format the HTML content from law articles for readability.

    Parameters:
        all_contents (str): The raw HTML content string.

    Returns:
        str: Cleaned and formatted text.
    """
    logger.info("Cleaning combined content for processing...")

    soup = BeautifulSoup(all_contents, "html.parser")

    for tag in soup.find_all(["br", "p"], string=lambda x: not x.strip()):
        tag.extract()

    clean_lines = []
    current_section = []

    for line in soup.stripped_strings:
        line = line.strip()
        if line.endswith(":") or line.startswith("- "):
            if current_section:
                clean_lines.append(" ".join(current_section))
                current_section = []
            clean_lines.append(line)
        else:
            current_section.append(line)

    if current_section:
        clean_lines.append(" ".join(current_section))

    clean_text = "\n\n".join(clean_lines)
    logger.debug("Formatted clean content: %s", clean_text)
    return clean_text


def clean_and_format_signataires(signataires_html):
    """
    Clean and format the HTML content of the signatories for readability.

    Parameters:
        signataires_html (str): The raw HTML content of the signatories.

    Returns:
        str: Cleaned and formatted list of signatories.
    """
    logger.info("Cleaning and formatting signatories...")

    soup = BeautifulSoup(signataires_html, "html.parser")

    signataires = []
    for p in soup.find_all("p"):
        text = " ".join(p.stripped_strings)
        if text:
            signataires.append(text)

    formatted_signataires = "\n".join(signataires)
    logger.debug("Formatted signatories: %s", formatted_signataires)
    return formatted_signataires


# Ensure the script runs directly
if __name__ == "__main__":
    main()
