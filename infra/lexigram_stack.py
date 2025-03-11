from aws_cdk import Stack
from constructs import Construct
from constructs.dynamo_db_table import LawPostsDynamoDBTable


class Lexigram(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        LawPostsDynamoDBTable(
            self,
            "LawPostsDynamoDBTable",
        )
