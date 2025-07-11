import logging
from typing import Any, Dict, Optional

from pylegifrance.fonds.loda import Loda

from app.agents.crew import create_crew
from app.config import api_client, settings
from app.errors.exceptions import (
    APIError,
    CrewError,
    DataParsingError,
    LegifranceError,
    PublishingError,
)
from app.errors.handlers import retry
from app.services.dynamo_utils import DynamoDBClient
from app.services.publisher import Publisher

logger = logging.getLogger(__name__)


class LawProcessingService:
    def __init__(self, dynamo_client: DynamoDBClient):
        self.dynamo_client = dynamo_client
        self.loda_api = Loda(api_client)
        self.publisher = Publisher(access_token=settings.access_token)

    def get_next_unprocessed_law(self) -> Optional[Dict[str, Any]]:
        """
        Get the next unprocessed law from DynamoDB.

        Returns:
            dict: Law information with textId and date, or None if no unprocessed laws
        """
        return self.dynamo_client.get_last_unprocessed_law()

    def fetch_law_details(self, text_id: str):
        """
        Fetch law details from Legifrance API.

        Args:
            text_id: The textId of the law to fetch

        Returns:
            TexteLoda: The law details object
        """
        try:
            law_details = self.loda_api.fetch(text_id)
            logger.info(f"Successfully fetched law details: {law_details.titre}")
            return law_details
        except Exception as e:
            raise LegifranceError(
                "Failed to fetch law details from Legifrance",
                original_exception=e,
                details={"law_id": text_id},
            ) from e

    @retry(max_attempts=2)
    def process_and_publish_law(self, law_info: Dict[str, Any], law_details) -> bool:
        """
        Process law details with crew and publish to Instagram.

        Args:
            law_info: Information about the law from DynamoDB
            law_details: TexteLoda object with law details

        Returns:
            bool: True if successfully processed and published
        """
        logger.info("Initializing the crew for content processing...")
        crew = create_crew()

        # Check if we have content to process
        if not law_details.texte_html and not law_details.articles:
            logger.info("No content available to process.")
            self._mark_law_as_processed(law_info)
            return True

        try:
            # Step 1: Clean and format the content
            clean_articles = self._format_law_content(law_details, law_info)

            # Step 2: Process with the crew
            image_generation, caption = self._process_with_crew(
                crew, law_details, clean_articles, law_info
            )

            # Step 3: Publish to Instagram
            published_id = self._publish_to_instagram(
                image_generation, caption, law_details, law_info
            )

            # Step 4: Mark as processed
            if published_id:
                self._mark_law_as_processed(law_info)
                logger.info("Law marked as processed in DynamoDB")
                return True
            else:
                raise PublishingError(
                    "Failed to get a valid publication ID",
                    details={"law_id": law_info["textId"]},
                )

        except Exception as error:
            logger.error(
                "Error processing and publishing law: %s",
                error,
                exc_info=True,
                extra={
                    "law_id": law_info["textId"],
                    "error_type": type(error).__name__,
                    "error_details": getattr(error, "details", {}),
                },
            )
            raise

    def _format_law_content(self, law_details, law_info: Dict[str, Any]) -> str:
        """Format law content using PyLegifrance's built-in formatting."""
        try:
            logger.info("Processing law content...")

            # Use PyLegifrance's built-in formatting
            if hasattr(law_details, "format_modifications_report"):
                clean_articles = law_details.format_modifications_report()
            elif law_details.texte_brut:
                clean_articles = law_details.texte_brut
            else:
                # Fallback to HTML content if other methods unavailable
                clean_articles = law_details.texte_html or ""

            return clean_articles

        except Exception as e:
            raise DataParsingError(
                "Error cleaning and formatting law content",
                original_exception=e,
                details={"law_id": law_info["textId"]},
            ) from e

    def _process_with_crew(
        self, crew, law_details, clean_articles: str, law_info: Dict[str, Any]
    ):
        """Process law content with the crew."""
        try:
            logger.info("Processing law content with the crew...")

            # Extract signatories if available
            signataires_content = ""
            if hasattr(law_details, "_texte") and hasattr(
                law_details._texte, "consult_response"
            ):
                consult_response = law_details._texte.consult_response
                if hasattr(consult_response, "signers") and consult_response.signers:
                    signataires_content = str(consult_response.signers)

            resume = crew.kickoff(
                inputs={
                    "titre": law_details.titre or "Titre non disponible",
                    "date_publication": law_details.date_publication.strftime(
                        "%d/%m/%Y"
                    )
                    if law_details.date_publication
                    else "Date non disponible",
                    "signataires": signataires_content,
                    "contenu": clean_articles,
                }
            )

            # Parse the crew output
            try:
                image_generation = resume.tasks_output[1].pydantic
                caption = resume.tasks_output[2].raw

                if not image_generation.image_url:
                    raise CrewError(
                        "Crew did not generate a valid image URL",
                        details={"crew_output": resume.tasks_output[1].raw},
                    )

                return image_generation, caption

            except (IndexError, AttributeError) as e:
                raise CrewError(
                    "Error accessing crew output",
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
                    details={"law_id": law_info["textId"]},
                ) from e
            raise

    def _publish_to_instagram(
        self, image_generation, caption: str, law_details, law_info: Dict[str, Any]
    ) -> str:
        """Publish content to Instagram."""
        try:
            logger.info("Publishing content to Instagram...")
            published_id = self.publisher.publish(
                image_url=image_generation.image_url, caption=caption
            )
            logger.info("Successfully published to Instagram with ID: %s", published_id)

            # Add a comment with the Legifrance URL if available
            if law_details.cid:
                try:
                    legifrance_url = (
                        f"https://www.legifrance.gouv.fr/jorf/id/{law_details.cid}"
                    )
                    self.publisher.comment_on_post(published_id, legifrance_url)
                    logger.info("Added Legifrance URL as comment: %s", legifrance_url)
                except Exception as e:
                    # Non-critical error, just log it
                    logger.warning(
                        "Failed to add Legifrance URL as comment: %s", str(e)
                    )

            return published_id

        except Exception as e:
            if not isinstance(e, (PublishingError, APIError)):
                raise PublishingError(
                    "Error publishing to Instagram",
                    original_exception=e,
                    details={"law_id": law_info["textId"]},
                ) from e
            raise

    def _mark_law_as_processed(self, law_info: Dict[str, Any]):
        """Mark a law as processed in DynamoDB."""
        key = {"textId": law_info["textId"]}
        updates = {"isProcessed": True}
        self.dynamo_client.update_item(key=key, updates=updates)
        logger.info("Law status updated to 'processed' in DynamoDB.")
