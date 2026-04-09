import platform
from pathlib import Path

import aws_cdk
from aws_cdk import (
    aws_events,
    aws_events_targets,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_s3,
    aws_secretsmanager,
)
from constructs import Construct
from dynamo_db_table import LawPostsDynamoDBTable


class Lexigram(aws_cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        law_posts_table = LawPostsDynamoDBTable(
            self,
            "LawPostsDynamoDBTable",
        )

        image_bucket = aws_s3.Bucket(
            self,
            "LexigramImageBucket",
            bucket_name="lexigram-generated-images",
            block_public_access=aws_s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                aws_s3.LifecycleRule(expiration=aws_cdk.Duration.days(30)),
            ],
        )
        image_bucket.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[image_bucket.arn_for_objects("*")],
                principals=[aws_iam.AnyPrincipal()],  # ty: ignore[invalid-argument-type]
            )
        )

        env_secret = aws_secretsmanager.Secret.from_secret_name_v2(
            self, "LexigramEnvSecrets", "my-env-secrets"
        )

        current_arch = platform.machine().lower()
        lambda_arch = (
            aws_lambda.Architecture.ARM_64
            if current_arch in ["arm64", "aarch64"]
            else aws_lambda.Architecture.X86_64
        )

        lambda_function = aws_lambda.DockerImageFunction(
            self,
            "LexigramLambdaFunction",
            code=aws_lambda.DockerImageCode.from_image_asset(
                directory=str(Path("./").resolve()),
            ),
            architecture=lambda_arch,
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            timeout=aws_cdk.Duration.minutes(10),
            memory_size=512,
        )

        lambda_function.add_environment("S3_BUCKET_NAME", image_bucket.bucket_name)
        lambda_function.add_environment(
            "DYNAMO_TABLE_NAME", law_posts_table.table.table_name
        )

        law_posts_table.table.grant_read_write_data(lambda_function)
        image_bucket.grant_put(lambda_function)
        lambda_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[env_secret.secret_arn],
            )
        )

        rule = aws_events.Rule(
            self,
            "LexigramLambdaSchedule",
            schedule=aws_events.Schedule.cron(
                minute="30", hour="11", week_day="MON-FRI"
            ),
        )
        target = aws_events_targets.LambdaFunction(
            lambda_function  # ty: ignore[invalid-argument-type]
        )
        rule.add_target(target)  # ty: ignore[invalid-argument-type]
