"""Evaluation fixtures — runs the full pipeline against real APIs.

Uses local Docker services for storage (no AWS credentials needed):
- DynamoDB Local (port 8000)
- MinIO for S3 (port 9090)
- Langfuse (port 3000)

Requires real credentials for: Legifrance, Mistral, Anthropic.
"""

import os

# Route boto3 to local Docker services — must be set before any boto3 imports
os.environ["AWS_ENDPOINT_URL_DYNAMODB"] = "http://localhost:8000"
os.environ["AWS_ENDPOINT_URL_S3"] = "http://localhost:9090"
os.environ.setdefault("AWS_ACCESS_KEY_ID", "minio")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "miniosecret")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-3")

import logging  # noqa: E402

import anthropic  # noqa: E402
import boto3  # noqa: E402
import dotenv  # noqa: E402
import litellm  # noqa: E402
import pytest  # noqa: E402
from langfuse import Langfuse, get_client, observe  # noqa: E402
from openinference.instrumentation.crewai import CrewAIInstrumentor  # noqa: E402
from pylegifrance.fonds.loda import Loda  # noqa: E402

from app.agents.crew import create_crew  # noqa: E402
from app.config import get_api_client, settings  # noqa: E402
from app.services.dynamo_utils import DynamoDBClient  # noqa: E402
from app.services.law_sync_service import LawSyncService  # noqa: E402

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

# Enable auto-instrumentation
CrewAIInstrumentor().instrument()
litellm.callbacks = ["langfuse"]

TABLE_NAME = "eval_law_posts"
BUCKET_NAME = "lexigram-images"


@pytest.fixture(scope="session", autouse=True)
def local_infra_setup():
    """Create DynamoDB table and verify S3 bucket on local Docker services."""
    # Create DynamoDB table on DynamoDB Local
    dynamodb = boto3.client("dynamodb")
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "textId", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "textId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info("Created DynamoDB table: %s", TABLE_NAME)
    except dynamodb.exceptions.ResourceInUseException:
        logger.info("DynamoDB table already exists: %s", TABLE_NAME)

    # Verify S3 bucket on MinIO (created by docker-compose entrypoint)
    s3 = boto3.client("s3")
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        logger.info("S3 bucket exists: %s", BUCKET_NAME)
    except Exception:
        s3.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-3"},
        )
        logger.info("Created S3 bucket: %s", BUCKET_NAME)

    # Override settings for eval
    settings.dynamo_table_name = TABLE_NAME
    settings.s3_bucket_name = BUCKET_NAME


@pytest.fixture(scope="session")
def langfuse_client():
    """Session-scoped Langfuse client using auto-initialized project keys."""
    client = Langfuse(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-lexigram-dev"),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-lexigram-dev"),
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
def dynamo_client(local_infra_setup):
    """Session-scoped DynamoDB client pointing to DynamoDB Local."""
    return DynamoDBClient(TABLE_NAME)


@pytest.fixture(scope="session")
def crew_result(dynamo_client, langfuse_client):
    """Run the full pipeline (excluding Instagram publishing) and return crew output.

    Uses Loda API directly to avoid instantiating Publisher (Instagram).
    """

    @observe(name="eval_pipeline")
    def run_pipeline():
        # Step 1: Sync laws from Legifrance to local DynamoDB
        law_sync_service = LawSyncService(dynamo_client)
        law_sync_service.sync_laws_for_year()

        # Step 2: Get next unprocessed law
        unprocessed_law = dynamo_client.get_oldest_unprocessed_law()
        assert unprocessed_law, "No unprocessed laws found in DynamoDB"
        logger.info("Evaluating law: %s", unprocessed_law["textId"])

        # Step 3: Fetch law details directly via Loda (avoids Publisher)
        loda_api = Loda(get_api_client())
        law_details = loda_api.fetch(unprocessed_law["textId"])
        assert law_details, f"Failed to fetch law: {unprocessed_law['textId']}"

        # Step 4: Format content
        if hasattr(law_details, "format_modifications_report"):
            clean_articles = law_details.format_modifications_report()
        elif law_details.texte_brut:
            clean_articles = law_details.texte_brut
        else:
            clean_articles = law_details.texte_html or ""

        # Step 5: Extract signatories
        signataires_content = ""
        if hasattr(law_details, "_texte") and hasattr(
            law_details._texte, "consult_response"
        ):
            consult_response = law_details._texte.consult_response
            if hasattr(consult_response, "signers") and consult_response.signers:
                signataires_content = str(consult_response.signers)

        # Step 6: Run crew
        crew = create_crew()
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

        trace_id = get_client().get_current_trace_id()
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
