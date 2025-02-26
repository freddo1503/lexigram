import os
from datetime import date

from crewai import LLM, Agent, Crew, Task
from dotenv import load_dotenv

from app.api_client import APIClient
from app.models import consult, loda
from app.models.loda import DateRange
from app.services.consult import fetch_legi_consult
from app.services.loda import fetch_loda_list

load_dotenv()

mistral_llm = LLM(
    model="mistral/mistral-large-latest", api_key=os.environ["MISTRAL_API_KEY"]
)


class AnalysteJuridique(Agent):
    """
    AnalysteJuridique is a legal analysis agent that leverages advanced language models to
    fetch, interpret, and analyze legal texts. It is designed to retrieve the latest laws,
    extract detailed legal insights, and provide clear, actionable summaries for its users.
    """

    def __init__(self, llm):
        super().__init__(
            role="Analyste Juridique Expert",
            goal="Fournir des analyses juridiques rigoureuses et des résumés clairs, précis et exploitables, adaptés aussi bien aux experts qu'aux non-juristes, en mettant en lumière les implications légales essentielles.",
            backstory=(
                "Vous êtes un analyste juridique chevronné, reconnu pour votre expertise en droit et votre capacité à simplifier des textes "
                "complexes sans en compromettre l’exactitude. Fort de votre expérience dans l’interprétation législative et réglementaire, "
                "vous identifiez les points essentiels, anticipez les implications juridiques et proposez des résumés concis et exploitables. "
                "Votre approche est méthodique, rigoureuse et pédagogique, garantissant une compréhension optimale pour toutes les parties prenantes."
            ),
            llm=llm,
        )
        object.__setattr__(
            self,
            "api_client",
            APIClient(
                base_url=os.environ["BASE_URL"],
                client_id=os.environ["CLIENT_ID"],
                client_secret=os.environ["CLIENT_SECRET"],
                token_url=os.environ["TOKEN_URL"],
            ),
        )

    def _try_fetch_details(self, law, index):
        """
        Attempt to fetch details for a given law and return the details if valid.
        """
        try:
            details = fetch_legi_consult(
                api_client=self.api_client,
                payload=consult.LegiConsultRequest(
                    date=law.lastUpdate,
                    textId=law.id,
                ),
            )
            if getattr(details, "title", None) and getattr(details, "articles", []):
                return details
        except Exception as e:
            print(f"Error fetching details for result index {index}: {e}")
        return None

    def fetch_latest_law(self):
        """
        Fetch the latest law that contains valid details.
        """
        lodal_list = fetch_loda_list(
            api_client=self.api_client,
            payload=loda.RequestPayload(
                sort="PUBLICATION_DATE_DESC",
                legalStatus=["VIGUEUR"],
                pageNumber=1,
                natures=["LOI"],
                secondSort="PUBLICATION_DATE_DESC",
                pageSize=10,
                publicationDate=DateRange(
                    start=date(date.today().year, 1, 1),
                    end=date(date.today().year, 12, 31),
                ),
            ),
        )
        # Ensure sorting in descending order of last update
        lodal_list.results = sorted(
            lodal_list.results, key=lambda x: x.lastUpdate, reverse=True
        )

        # Iterate over the sorted laws and return details of the first valid one
        for idx, law in enumerate(lodal_list.results):
            details = self._try_fetch_details(law, idx)
            if details:  # Only return the first valid law
                return details.model_dump(mode="json")
            else:
                print(f"Skipping law at index {idx}: No valid details found.")

        # No valid law found
        return {
            "titre": "",
            "content": "Aucun détail valide n'a été trouvé pour les lois récentes.",
        }

    def analyze_data(self, data):
        """
        Analyze the legal text and return a summary.
        """
        if data:
            task = Task(
                description=(
                    "Analyser le texte juridique suivant et fournir un résumé court, clair et accessible aux non-juristes, "
                    "au format optimisé pour Instagram. Le résumé doit inclure :\n"
                    "1. Titre du texte juridique : {titre}\n"
                    "2. Date de publication : {date_publication}\n"
                    "3. Signataires officiels : {signataires}\n"
                    "4. Synthèse des points clés en langage simple : {contenu}"
                ),
                expected_output=(
                    "Résumé simplifié comprenant : "
                    "- Titre du texte juridique, "
                    "- Date de publication, "
                    "- Signataires, "
                    "- Synthèse claire et accessible des principaux points."
                ),
                agent=self,
            )

            crew = Crew(agents=[self], tasks=[task])

            resume = crew.kickoff(
                inputs={
                    "titre": data["title"],
                    "date_publication": data["dateParution"],
                    "signataires": data["signers"],
                    "contenu": data["articles"][0],
                }
            )

            return resume
        return "Aucune donnée à analyser."
