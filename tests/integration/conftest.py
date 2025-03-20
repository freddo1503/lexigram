import os

import dotenv
import pytest

from app.api_client import LegifranceApiClient
from infra.dynamo_db_table import LawPostSchema

dotenv.load_dotenv()

BASE_URL = os.environ["BASE_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
TOKEN_URL = os.environ["TOKEN_URL"]


@pytest.fixture(scope="session")
def api_client():
    client = LegifranceApiClient(
        base_url=BASE_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_url=TOKEN_URL,
    )
    return client


@pytest.fixture(scope="function")
def table_name():
    table_name = LawPostSchema().table_name
    return table_name
