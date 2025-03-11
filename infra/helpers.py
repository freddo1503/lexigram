import os

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError


def get_account_and_region(profile: str = None):
    if not profile and not os.getenv("AWS_PROFILE"):
        raise ValueError("No profile provided")

    session = boto3.Session(profile_name=profile or os.getenv("AWS_PROFILE"))

    try:
        sts_client = session.client("sts")
        data = sts_client.get_caller_identity()
        region = session.region_name

        return {
            "account": data.get("Account"),
            "region": region,
        }

    except (NoCredentialsError, PartialCredentialsError) as e:
        raise ValueError("Error with AWS credentials") from e
