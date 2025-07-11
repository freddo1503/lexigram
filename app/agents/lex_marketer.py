from crewai import LLM, Agent

from app.config import agents_config, settings


class LexMarker(Agent):
    """
    LexMarker est un expert en mise en forme et diffusion de résumés juridiques sur Instagram.
    Il transforme les analyses de l'Analyste Juridique en contenus clairs, engageants et adaptés aux réseaux sociaux.
    """

    def __init__(self):
        agent_config = agents_config["agents"]["lex_marketer"]
        super().__init__(
            role=agent_config["role"],
            goal=agent_config["goal"],
            backstory=agent_config["backstory"],
            llm=LLM(
                model="mistral/mistral-large-latest",
                api_key=settings.mistral_api_key,
            ),
            allow_delegation=False,
            verbose=True,
        )
