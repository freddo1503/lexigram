from crewai import LLM, Agent

from app.config import agents_config, settings


class AnalysteJuridique(Agent):
    """
    AnalysteJuridique est un agent spécialisé dans l'analyse et l'interprétation des textes légaux.
    Il extrait les points clés des lois et réglementations pour produire des analyses précises.
    """

    def __init__(self):
        agent_config = agents_config["agents"]["analyste_juridique"]
        super().__init__(
            role=agent_config["role"],
            goal=agent_config["goal"],
            backstory=agent_config["backstory"],
            llm=LLM(
                model="mistral/mistral-large-latest",
                api_key=settings.mistral_api_key,
            ),
            verbose=True,
        )
