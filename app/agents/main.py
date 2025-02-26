import json

from crew import create_crew

from app.agents.tools import fetch_latest_law
from app.config import api_client


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

    image_data = json.loads(resume.tasks_output[1].raw)
    print("\nIMAGE_URL: ", image_data["image_url"])
    print("\nTEXT_URL: ", resume.tasks_output[0].raw)


# Ensure this script runs directly
if __name__ == "__main__":
    main()
