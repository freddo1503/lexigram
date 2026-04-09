import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_typing.events import EventBridgeEvent

from app.main import main

logger = Logger(service="lexigram")


@logger.inject_lambda_context
def handler(event: EventBridgeEvent, context: LambdaContext):
    logger.info(
        "Lambda function started",
        extra={
            "event_source": event.get("source"),
            "event_time": event.get("time"),
        },
    )
    try:
        main()
        return {"statusCode": 200, "body": json.dumps("Success")}
    except Exception:
        logger.exception("Lexigram handler failed")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": "internal_server_error",
                    "request_id": context.aws_request_id,
                }
            ),
        }
