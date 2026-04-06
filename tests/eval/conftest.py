"""Evaluation fixtures — runs the full pipeline against real APIs."""

import logging
import os

import anthropic
import dotenv
import litellm
import pytest
from langfuse import Langfuse
from langfuse.decorators import (  # ty: ignore[unresolved-import]
    langfuse_context,
    observe,
)
from openinference.instrumentation.crewai import CrewAIInstrumentor

from app.agents.crew import create_crew
from app.config import settings
from app.services.dynamo_utils import DynamoDBClient
from app.services.law_processing_service import LawProcessingService
from app.services.law_sync_service import LawSyncService

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

# Enable auto-instrumentation
CrewAIInstrumentor().instrument()
litellm.callbacks = ["langfuse"]


@pytest.fixture(scope="session")
def langfuse_client():
    """Session-scoped Langfuse client."""
    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3000"),
    )
    assert client.auth_check(), "Langfuse authentication failed"
    yield client
    client.flush()


@pytest.fixture(scope="session")
def anthropic_client():
    """Session-scoped Anthropic client for Claude Opus judge."""
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


@pytest.fixture(scope="session")
def dynamo_client():
    """Session-scoped DynamoDB client."""
    assert settings.dynamo_table_name, "DYNAMO_TABLE_NAME must be set"
    return DynamoDBClient(settings.dynamo_table_name)


@pytest.fixture(scope="session")
def crew_result(dynamo_client, langfuse_client):
    """Run the full pipeline (excluding Instagram publishing) and return crew output.

    This fixture:
    1. Syncs laws from Legifrance
    2. Gets the next unprocessed law
    3. Fetches law details
    4. Runs the CrewAI pipeline
    5. Returns the crew result with all task outputs
    """

    @observe(name="eval_pipeline")
    def run_pipeline():
        law_sync_service = LawSyncService(dynamo_client)
        law_processing_service = LawProcessingService(dynamo_client)

        # Step 1: Sync laws
        law_sync_service.sync_laws_for_year()

        # Step 2: Get next unprocessed law
        unprocessed_law = law_processing_service.get_next_unprocessed_law()
        assert unprocessed_law, "No unprocessed laws found in DynamoDB"
        logger.info("Evaluating law: %s", unprocessed_law["textId"])

        # Step 3: Fetch law details
        law_details = law_processing_service.fetch_law_details(
            unprocessed_law["textId"]
        )

        # Step 4: Format content
        clean_articles = law_processing_service._format_law_content(
            law_details, unprocessed_law
        )

        # Step 5: Run crew
        crew = create_crew()

        signataires_content = ""
        if hasattr(law_details, "_texte") and hasattr(
            law_details._texte, "consult_response"
        ):
            consult_response = law_details._texte.consult_response
            if hasattr(consult_response, "signers") and consult_response.signers:
                signataires_content = str(consult_response.signers)

        result = crew.kickoff(
            inputs={
                "titre": law_details.titre or "Titre non disponible",
                "date_publication": law_details.date_publication.strftime("%d/%m/%Y")
                if law_details.date_publication
                else "Date non disponible",
                "signataires": signataires_content,
                "contenu": clean_articles,
            }
        )

        # Store trace_id for scoring
        trace_id = langfuse_context.get_current_trace_id()

        return result, trace_id, unprocessed_law

    result, trace_id, law_info = run_pipeline()
    langfuse_client.flush()

    return {
        "result": result,
        "trace_id": trace_id,
        "law_info": law_info,
    }


@pytest.fixture(scope="session")
def text_summary_output(crew_result):
    """Extract text summary task output."""
    return crew_result["result"].tasks_output[0]


@pytest.fixture(scope="session")
def image_generation_output(crew_result):
    """Extract image generation task output."""
    return crew_result["result"].tasks_output[1]


@pytest.fixture(scope="session")
def caption_output(crew_result):
    """Extract caption task output."""
    return crew_result["result"].tasks_output[2]


@pytest.fixture(scope="session")
def trace_id(crew_result):
    """Extract Langfuse trace ID."""
    return crew_result["trace_id"]
