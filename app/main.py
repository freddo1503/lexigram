import logging

from app.config import settings
from app.errors.exceptions import (
    DynamoDBError,
    LexigramError,
)
from app.services.dynamo_utils import DynamoDBClient
from app.services.law_processing_service import LawProcessingService
from app.services.law_sync_service import LawSyncService

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
        dynamo_client = DynamoDBClient(settings.dynamo_table_name)

        # Initialize services
        law_sync_service = LawSyncService(dynamo_client)
        law_processing_service = LawProcessingService(dynamo_client)

        # Step 1: Sync DynamoDB with the latest laws from the API
        try:
            logger.info("Step 1: Synchronizing DynamoDB with latest laws")
            law_sync_service.sync_laws_for_year()
        except Exception as e:
            if not isinstance(e, DynamoDBError):
                raise DynamoDBError(
                    "Failed to synchronize DynamoDB with latest laws",
                    original_exception=e,
                ) from e
            raise

        # Step 2: Get the next unprocessed law
        try:
            logger.info("Step 2: Retrieving oldest unprocessed law")
            unprocessed_law = law_processing_service.get_next_unprocessed_law()

            if not unprocessed_law:
                logger.info("No unprocessed laws found. Workflow complete.")
                return

            logger.info("Found unprocessed law: %s", unprocessed_law["textId"])
        except Exception as e:
            if not isinstance(e, DynamoDBError):
                raise DynamoDBError(
                    "Failed to retrieve oldest unprocessed law", original_exception=e
                ) from e
            raise

        # Step 3: Fetch law details from Legifrance
        try:
            logger.info("Step 3: Fetching law details from Legifrance")
            law_details = law_processing_service.fetch_law_details(
                unprocessed_law["textId"]
            )
        except Exception as e:
            logger.error("Failed to fetch law details: %s", str(e))
            raise

        # Step 4: Process and publish the law
        try:
            logger.info("Step 4: Processing and publishing law")
            law_processing_service.process_and_publish_law(unprocessed_law, law_details)
            logger.info("Lexigram workflow completed successfully")
        except Exception as e:
            logger.error("Failed to process and publish law: %s", str(e))
            raise

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


# Ensure the script runs directly
if __name__ == "__main__":
    main()
