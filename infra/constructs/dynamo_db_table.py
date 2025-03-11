import re

from aws_cdk import aws_dynamodb
from constructs import Construct
from pydantic import BaseModel, Field


class LawPostSchema(BaseModel):
    partition_key: dict = Field(
        default={"name": "textId", "type": aws_dynamodb.AttributeType.STRING},
        description="Default partition key with name 'textId' and type STRING.",
    )
    sort_key: dict = Field(
        default={"name": "date", "type": aws_dynamodb.AttributeType.STRING},
        description="Default sort key with name 'date' and type STRING.",
    )
    attributes: dict = Field(
        default={
            "date": aws_dynamodb.AttributeType.STRING,
            "isProcessed": aws_dynamodb.AttributeType.STRING,
        },
        description="Additional attributes for the table.",
    )

    @property
    def table_name(self) -> str:
        # Dynamically return the class name in snake_case as the table name
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__class__.__name__).lower()


class LawPostsDynamoDBTable(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        schema: LawPostSchema = LawPostSchema(),
        billing_mode: aws_dynamodb.BillingMode = aws_dynamodb.BillingMode.PAY_PER_REQUEST,
    ):
        """
        Initializes the LawPostsDynamoDBTable.

        :param scope: The parent construct.
        :param id: The ID for this construct.
        :param schema: A Pydantic model defining the table name and key attributes.
        :param billing_mode: The billing mode for the table.
        """
        super().__init__(scope, id)

        # Define key attributes
        partition_key = aws_dynamodb.Attribute(
            name=schema.partition_key["name"], type=schema.partition_key["type"]
        )

        sort_key = (
            aws_dynamodb.Attribute(
                name=schema.sort_key["name"], type=schema.sort_key["type"]
            )
            if schema.sort_key
            else None
        )

        # Use schema.table_name dynamically from the __class__.__name__
        self.table = aws_dynamodb.Table(
            self,
            "LawPostsTable",
            table_name=schema.table_name,
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=billing_mode,
        )
