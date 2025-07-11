import boto3
import dotenv
import pytest
from pylegifrance import ApiConfig, LegifranceClient

from app.config import (
    DYNAMO_TABLE_NAME,
)
from app.services.dynamo_utils import DynamoDBClient

dotenv.load_dotenv()


@pytest.fixture(scope="session")
def api_client():
    config = ApiConfig.from_env()
    return LegifranceClient(config=config)


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
