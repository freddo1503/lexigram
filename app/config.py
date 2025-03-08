import os

import dotenv

from app.api_client import APIClient

dotenv.load_dotenv()

api_client = APIClient(
    base_url=os.environ["BASE_URL"],
    client_id=os.environ["CLIENT_ID"],
    client_secret=os.environ["CLIENT_SECRET"],
    token_url=os.environ["TOKEN_URL"],
)

open_api_key = os.environ["OPENAI_API_KEY"]
mistral_api_key = os.environ["MISTRAL_API_KEY"]
access_token = os.environ["ACCESS_TOKEN"]
