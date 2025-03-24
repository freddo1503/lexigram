import json
from pathlib import Path

import aws_cdk
import boto3
from constructs import Construct
from dotenv import dotenv_values
from dynamo_db_table import LawPostsDynamoDBTable


class Lexigram(aws_cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        LawPostsDynamoDBTable(
            self,
            "LawPostsDynamoDBTable",
        )

        SecretsManagerConstruct(
            self, "LexigramEnvSecrets", secret_name="my-env-secrets"
        )


class SecretsManagerConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        env_file_path: Path = Path(".env"),
        secret_name: str = "my-env-secrets",
    ):
        super().__init__(scope, id)
        env_vars = dotenv_values(env_file_path)
        secret_value = json.dumps(env_vars)
        self.create_or_update_secret(secret_name, secret_value)

    def create_or_update_secret(self, secret_name: str, secret_value: str):
        client = boto3.client("secretsmanager")

        try:
            client.describe_secret(SecretId=secret_name)
            client.put_secret_value(SecretId=secret_name, SecretString=secret_value)
        except client.exceptions.ResourceNotFoundException:
            client.create_secret(Name=secret_name, SecretString=secret_value)
        except Exception as e:
            print(f"An error occurred while managing the secret: {e}")
