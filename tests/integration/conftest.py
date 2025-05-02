import boto3
import dotenv
import pytest

from app.api_client import LegifranceApiClient
from app.config import (
    DYNAMO_TABLE_NAME,
    LEGIFRANCE_API_URL,
    LEGIFRANCE_CLIENT_ID,
    LEGIFRANCE_CLIENT_SECRET,
    LEGIFRANCE_TOKEN_URL,
)
from app.services.dynamo_utils import DynamoDBClient

dotenv.load_dotenv()


@pytest.fixture(scope="session")
def api_client():
    client = LegifranceApiClient(
        base_url=LEGIFRANCE_API_URL,
        client_id=LEGIFRANCE_CLIENT_ID,
        client_secret=LEGIFRANCE_CLIENT_SECRET,
        token_url=LEGIFRANCE_TOKEN_URL,
    )
    return client


@pytest.fixture(scope="function")
def table_name():
    table_name = DYNAMO_TABLE_NAME
    return table_name


@pytest.fixture
def dynamodb_client(table_name):
    """Fixture to initialize the DynamoDB client."""
    return DynamoDBClient(table_name)


@pytest.fixture
def dynamo_table(table_name):
    """Fixture to initialize the DynamoDB table."""
    return boto3.resource("dynamodb").Table(table_name)


@pytest.fixture
def secrets_manager_client():
    return boto3.client("secretsmanager", region_name="eu-west-3")
