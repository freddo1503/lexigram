import json
import logging
from datetime import date

from bs4 import BeautifulSoup

from app import config
from app.agents.crew import create_crew
from app.config import api_client
from app.errors.exceptions import (
    APIError,
    CrewError,
    DataParsingError,
    DynamoDBError,
    LegifranceError,
    LexigramError,
    PublishingError,
)
from app.errors.handlers import retry
from app.models import consult, loda
from app.models.consult import LegiConsultResponse
from app.services.dynamo_utils import DynamoDBClient
from app.services.legifrance import extract_legifrance_url, fetch_legi_consult
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
    try:
        logger.info("Starting Lexigram workflow")
        dynamo_client = init_dynamo_client()

        # Step 1: Sync DynamoDB with the latest laws from the API
        try:
            logger.info("Step 1: Synchronizing DynamoDB with latest laws")
            sync_dynamodb_with_latest_laws(dynamo_client)
        except Exception as e:
            if not isinstance(e, DynamoDBError):
                raise DynamoDBError(
                    "Failed to synchronize DynamoDB with latest laws",
                    original_exception=e,
                ) from e
            raise

        # Step 2: Retrieve the oldest unprocessed law
        try:
            logger.info("Step 2: Retrieving oldest unprocessed law")
            last_unprocessed_law = dynamo_client.get_last_unprocessed_law()

            if not last_unprocessed_law:
                logger.info("No unprocessed laws found. Workflow complete.")
                return

            logger.info("Found unprocessed law: %s", last_unprocessed_law["textId"])
        except Exception as e:
            if not isinstance(e, DynamoDBError):
                raise DynamoDBError(
                    "Failed to retrieve oldest unprocessed law", original_exception=e
                ) from e
            raise

        # Step 3: Fetch law details from Legifrance
        try:
            logger.info("Step 3: Fetching law details from Legifrance")
            law_details = fetch_law_details_from_legifrance(last_unprocessed_law)
            logger.info("Successfully fetched law details: %s", law_details.title)
        except Exception as e:
            if not isinstance(e, LegifranceError):
                raise LegifranceError(
                    "Failed to fetch law details from Legifrance",
                    original_exception=e,
                    details={"law_id": last_unprocessed_law["textId"]},
                ) from e
            raise

        # Step 4: Process and publish the law using the crew
        logger.info("Step 4: Processing and publishing law")
        process_and_publish_law(dynamo_client, last_unprocessed_law, law_details)

        logger.info("Lexigram workflow completed successfully")

    except LexigramError as e:
        logger.error(
            "Lexigram workflow failed: %s",
            e.message,
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_details": getattr(e, "details", {}),
            },
        )
        raise
    except Exception as e:
        logger.critical(
            "Unexpected error in Lexigram workflow: %s", str(e), exc_info=True
        )
        raise


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


@retry(max_attempts=2)  # Limited retries for the whole process
def process_and_publish_law(dynamo_client, last_law, law_details: LegiConsultResponse):
    """
    Process the law details with the crew, generate content, and publish it to Instagram.

    Parameters:
        dynamo_client (DynamoDBClient): DynamoDB client object.
        last_law (dict): Information of the last unprocessed law.
        law_details (LegiConsultResponse): Details of the law fetched from Legifrance.

    Raises:
        CrewError: If there's an error in the crew processing.
        PublishingError: If there's an error publishing to Instagram.
        DataParsingError: If there's an error parsing data.
        LexigramError: For other application-specific errors.
    """
    logger.info("Initializing the crew for content processing...")
    crew = create_crew()

    articles = getattr(law_details, "articles", [])
    if not articles or not articles[0]:
        logger.info("No articles available to process.")
        update_processed_law_status(dynamo_client, last_law)
        return

    try:
        # Step 1: Clean and format the content
        try:
            logger.info("Combining content from articles...")
            all_contents = "\n\n".join(article.content for article in articles)
            clean_articles = clean_and_format_content(all_contents)
            clean_signataires = clean_and_format_signataires(law_details.signers)
        except Exception as e:
            raise DataParsingError(
                "Error cleaning and formatting law content",
                original_exception=e,
                details={"law_id": last_law["textId"]},
            ) from e

        # Step 2: Process with the crew
        try:
            logger.info("Processing law content with the crew...")
            resume = crew.kickoff(
                inputs={
                    "titre": law_details.title,
                    "date_publication": law_details.dateParution,
                    "signataires": clean_signataires,
                    "contenu": clean_articles,
                }
            )

            # Parse the crew output
            try:
                image_generation = json.loads(resume.tasks_output[1].raw)
                caption = resume.tasks_output[2].raw

                if not image_generation.get("image_url"):
                    raise CrewError(
                        "Crew did not generate a valid image URL",
                        details={"crew_output": resume.tasks_output[1].raw},
                    )
            except (IndexError, json.JSONDecodeError) as e:
                raise CrewError(
                    "Error parsing crew output",
                    original_exception=e,
                    details={
                        "crew_output": str(resume.tasks_output)
                        if hasattr(resume, "tasks_output")
                        else "No output"
                    },
                ) from e
        except Exception as e:
            if not isinstance(e, CrewError):
                raise CrewError(
                    "Error in crew processing",
                    original_exception=e,
                    details={"law_id": last_law["textId"]},
                ) from e
            raise

        # Step 3: Publish to Instagram
        try:
            logger.info("Publishing content to Instagram...")
            publisher = Publisher(access_token=config.ACCESS_TOKEN)
            published_id = publisher.publish(
                image_url=image_generation.get("image_url"), caption=caption
            )
            logger.info("Successfully published to Instagram with ID: %s", published_id)

            # Add a comment with the Legifrance URL if available
            if law_details.cid:
                try:
                    legifrance_url = extract_legifrance_url(law_details)
                    publisher.comment_on_post(published_id, legifrance_url)
                    logger.info("Added Legifrance URL as comment: %s", legifrance_url)
                except Exception as e:
                    # Non-critical error, just log it
                    logger.warning(
                        "Failed to add Legifrance URL as comment: %s", str(e)
                    )

            # Mark as processed only if successfully published
            if published_id:
                update_processed_law_status(dynamo_client, last_law)
                logger.info("Law marked as processed in DynamoDB")
            else:
                raise PublishingError(
                    "Failed to get a valid publication ID",
                    details={"law_id": last_law["textId"]},
                )
        except Exception as e:
            if not isinstance(e, (PublishingError, APIError)):
                raise PublishingError(
                    "Error publishing to Instagram",
                    original_exception=e,
                    details={"law_id": last_law["textId"]},
                ) from e
            raise

    except Exception as error:
        # Log the error with detailed information
        logger.error(
            "Error processing and publishing law: %s",
            error,
            exc_info=True,
            extra={
                "law_id": last_law["textId"],
                "error_type": type(error).__name__,
                "error_details": getattr(error, "details", {}),
            },
        )
        # Re-raise to allow for retry or proper handling by the caller
        raise


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
