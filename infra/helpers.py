import os

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError


def get_account_and_region(profile: str = None):
    """
    Get the AWS account ID and region using either an AWS profile or environment variables.

    Args:
        profile (str, optional): The AWS profile to use. Defaults to None.

    Returns:
        dict: A dictionary containing the account ID and region.

    Raises:
        ValueError: If no valid AWS configuration is found or credentials are invalid.
    """
    profile = profile or os.getenv("AWS_PROFILE")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("CDK_DEFAULT_REGION")

    if not profile and not (access_key and secret_key and region):
        raise ValueError(
            "No valid AWS configuration found. Provide one of the following:\n"
            "- AWS_PROFILE\n"
            "- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and CDK_DEFAULT_REGION or AWS_REGION"
        )

    try:
        session = (
            boto3.Session(profile_name=profile)
            if profile
            else boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
        )

        sts_client = session.client("sts")
        account_id = sts_client.get_caller_identity().get("Account")
        session_region = session.region_name or region

        return {
            "account": account_id,
            "region": session_region,
        }

    except (NoCredentialsError, PartialCredentialsError):
        raise ValueError("Invalid AWS credentials. Please check your configuration.")
