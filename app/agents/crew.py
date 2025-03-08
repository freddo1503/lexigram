from crewai import Crew

from app.agents.lex_analyst import AnalysteJuridique
from app.agents.lex_marketer import LexMarker
from app.agents.lex_pictor import LexPictor
from app.agents.task import caption, image_generation, text_summary


def create_crew():
    lex_analyst = AnalysteJuridique()
    lex_pictor = LexPictor()
    lex_marketer = LexMarker()
    text_summary.agent = lex_analyst
    image_generation.agent = lex_pictor
    caption.agent = lex_marketer
    return Crew(
        agents=[lex_analyst, lex_pictor, lex_marketer],
        tasks=[text_summary, image_generation, caption],
    )
