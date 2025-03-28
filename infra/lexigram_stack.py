import json
from pathlib import Path

import aws_cdk
import boto3
from aws_cdk import aws_iam, aws_lambda, aws_logs
from constructs import Construct
from dotenv import dotenv_values
from dynamo_db_table import LawPostsDynamoDBTable


class Lexigram(aws_cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        law_posts_table = LawPostsDynamoDBTable(
            self,
            "LawPostsDynamoDBTable",
        )

        secret = SecretsManagerConstruct(
            self, "LexigramEnvSecrets", secret_name="my-env-secrets"
        )

        lambda_function = aws_lambda.DockerImageFunction(
            self,
            "LexigramLambdaFunction",
            code=aws_lambda.DockerImageCode.from_image_asset(
                working_directory="/tmp",
                directory=str(Path("./").resolve()),
            ),
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            timeout=aws_cdk.Duration.minutes(2),
            memory_size=1024,
        )

        law_posts_table.table.grant_read_write_data(lambda_function)
        lambda_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[secret.secret_arn],
            )
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
        self.secret_arn = None

        env_vars = dotenv_values(env_file_path)
        secret_value = json.dumps(env_vars)

        self.secret_arn = self.create_or_update_secret(secret_name, secret_value)

    def create_or_update_secret(
        self, secret_name: str, secret_value: str
    ) -> str | None:
        client = boto3.client("secretsmanager")

        try:
            response = client.describe_secret(SecretId=secret_name)
            client.put_secret_value(SecretId=secret_name, SecretString=secret_value)
            print(f"Updated existing secret: {secret_name}")
        except client.exceptions.ResourceNotFoundException:
            response = client.create_secret(Name=secret_name, SecretString=secret_value)
            print(f"Created new secret: {secret_name}")
        except Exception as e:
            print(f"An error occurred while managing the secret: {e}")
            return None

        return response["ARN"]
