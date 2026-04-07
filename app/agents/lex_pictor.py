import os
import uuid
from typing import Type

import boto3
from crewai import LLM, Agent
from crewai.tools import BaseTool
from mistralai import Mistral
from pydantic import BaseModel

from app.config import agents_config, settings
from app.models.lex_pictor import ImagePayload


class ImagePromptSchema(BaseModel):
    """Input schema for Mistral Image Tool."""

    image_description: str


class MistralImageTool(BaseTool):
    name: str = "Mistral Image Tool"
    description: str = "Generates images using Mistral's Agents API image generation."
    args_schema: Type[BaseModel] = ImagePromptSchema

    def _run(self, **kwargs) -> ImagePayload | str:
        image_description = kwargs.get("image_description")
        if not image_description:
            return "Image description is required."

        client = Mistral(api_key=settings.mistral_api_key)

        # Create an agent with image generation tool
        agent = client.beta.agents.create(
            model="mistral-medium-latest",
            name="Lexigram Image Generator",
            tools=[{"type": "image_generation"}],
        )

        # Start a conversation with the image prompt
        response = client.beta.conversations.start(
            agent_id=agent.id,
            inputs=image_description,
        )

        # Extract file_id from the response outputs
        file_id = None
        for output in response.outputs:
            if hasattr(output, "file_id") and output.file_id:
                file_id = output.file_id
                break

        if not file_id:
            return "Image generation returned no file."

        # Download the generated image
        file_bytes = client.files.download(file_id=file_id).read()

        # Upload to S3
        s3_key = f"images/{uuid.uuid4()}.png"
        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_bytes,
            ContentType="image/png",
        )

        # Construct public URL (supports both AWS S3 and S3-compatible endpoints)
        s3_endpoint = os.environ.get("AWS_ENDPOINT_URL_S3")
        if s3_endpoint:
            image_url = f"{s3_endpoint}/{settings.s3_bucket_name}/{s3_key}"
        else:
            image_url = (
                f"https://{settings.s3_bucket_name}.s3.eu-west-3.amazonaws.com/{s3_key}"
            )

        return ImagePayload(
            image_url=image_url,
            image_description=image_description,
        )


class LexPictor(Agent):
    """
    LexPictor generates an image based on what the law inspires, using the output of a legal analysis.
    It leverages the latest legal text and analysis provided by the AnalysteJuridique agent.
    """

    def __init__(self):
        agent_config = agents_config["agents"]["lex_pictor"]
        super().__init__(
            role=agent_config["role"],
            goal=agent_config["goal"],
            backstory=agent_config["backstory"],
            llm=LLM(
                model="mistral/mistral-large-latest",
                api_key=settings.mistral_api_key,
            ),
            tools=[MistralImageTool()],
            allow_delegation=False,
            verbose=True,
        )
