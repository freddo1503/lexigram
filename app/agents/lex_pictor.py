import json
from typing import Type

from crewai import LLM, Agent
from crewai.tools import BaseTool
from openai import OpenAI
from pydantic import BaseModel

from app import config


class ImagePromptSchema(BaseModel):
    """Input schema for Dall-E Tool."""

    image_description: str


class DallETool(BaseTool):
    name: str = "Dall-E Tool"
    description: str = "Generates images using OpenAI's Dall-E model."
    args_schema: Type[BaseModel] = ImagePromptSchema

    def _run(self, **kwargs) -> str:
        client = OpenAI(api_key=config.open_api_key)

        image_description = kwargs.get("image_description")

        if not image_description:
            return "Image description is required."

        response = client.images.generate(
            model="dall-e-3",
            prompt=image_description,
            size="1024x1024",
            n=1,
        )

        image_data = json.dumps(
            {
                "image_url": response.data[0].url,
                "image_description": response.data[0].revised_prompt,
            }
        )

        return image_data


class LexPictor(Agent):
    """
    LexPictor generates an image based on what the law inspires, using the output of a legal analysis.
    It leverages the latest legal text and analysis provided by the AnalysteJuridique agent.
    """

    def __init__(self):
        super().__init__(
            role="Artiste Visuel Innovant",
            goal=(
                "Créer des oeuvres d'art visuelles captivantes et originales en utilisant des techniques numériques avancées, "
                "visant à évoquer des émotions profondes et à communiquer des concepts complexes de manière accessible et esthétique."
            ),
            backstory=(
                "LexPictor est un artiste visuel passionné, spécialisé dans l'intégration de technologies numériques pour produire des illustrations "
                "et des animations qui transcendent les formes d'art traditionnelles. Avec une formation en beaux-arts et une maîtrise des outils numériques modernes, "
                "LexPictor fusionne créativité artistique et innovation technologique pour explorer de nouveaux horizons visuels. Son travail est reconnu pour sa capacité "
                "à transformer des idées abstraites en représentations visuelles tangibles, engageant un large public et suscitant réflexion et admiration."
            ),
            llm=LLM(model="gpt-4", api_key=config.open_api_key),
            tools=[DallETool()],
            allow_delegation=False,
            verbose=True,
        )
