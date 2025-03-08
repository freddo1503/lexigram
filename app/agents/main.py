import os

from app.agents.crew import create_crew
from app.agents.tools import fetch_latest_law
from app.config import api_client

os.environ["OTEL_SDK_DISABLED"] = "true"


def main():
    # Initialize the crew
    crew = create_crew()

    # Fetch the latest law data
    data = fetch_latest_law(api_client=api_client)

    # Pass the data to kickoff function of the crew
    resume = crew.kickoff(
        inputs={
            "titre": data["title"],
            "date_publication": data["dateParution"],
            "signataires": data["signers"],
            "contenu": data["articles"][0]["content"],
        }
    )

    print(resume.tasks_output[0].raw)
    print(resume.tasks_output[1].raw)
    print(resume.tasks_output[2].raw)


# Ensure this script runs directly
if __name__ == "__main__":
    main()
