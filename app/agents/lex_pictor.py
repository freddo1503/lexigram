from typing import Type

from crewai import LLM, Agent
from crewai.tools import BaseTool
from openai import OpenAI
from pydantic import BaseModel

from app.config import agents_config, settings
from app.models.lex_pictor import ImagePayload


class ImagePromptSchema(BaseModel):
    """Input schema for Dall-E Tool."""

    image_description: str


class DallETool(BaseTool):
    name: str = "Dall-E Tool"
    description: str = "Generates images using OpenAI's Dall-E model."
    args_schema: Type[BaseModel] = ImagePromptSchema

    def _run(self, **kwargs) -> ImagePayload | str:
        client = OpenAI(api_key=settings.openai_api_key)
        image_description = kwargs.get("image_description")
        if not image_description:
            return "Image description is required."
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_description,
            size="1024x1024",
            n=1,
        )
        return ImagePayload(
            image_url=response.data[0].url,
            image_description=response.data[0].revised_prompt,
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
            llm=LLM(model="gpt-4", api_key=settings.openai_api_key),
            tools=[DallETool()],
            allow_delegation=False,
            verbose=True,
        )
