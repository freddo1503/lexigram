import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_typing.events import EventBridgeEvent

from app.main import main

logger = Logger(service="lexigram")


@logger.inject_lambda_context
def handler(event: EventBridgeEvent, context: LambdaContext):
    logger.info("Lambda function started with event: %s", event)
    try:
        main()
        return {"statusCode": 200, "body": json.dumps("Success")}
    except Exception as e:
        logger.error("Error occurred: %s", str(e))
        return {"statusCode": 500, "body": json.dumps(str(e))}
