from crewai import Crew

from app.agents.lex_analyst import AnalysteJuridique
from app.agents.lex_pictor import LexPictor
from app.agents.task import image_generation, text_summary


def create_crew():
    lex_analyst = AnalysteJuridique()
    lex_pictor = LexPictor()
    text_summary.agent = lex_analyst
    image_generation.agent = lex_pictor
    return Crew(
        agents=[lex_analyst, lex_pictor], tasks=[text_summary, image_generation]
    )
