import json
import os

from app import config
from app.agents.crew import create_crew
from app.agents.tools import fetch_latest_law
from app.config import api_client
from app.services.publisher import Publisher

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

    image_generation = json.loads(resume.tasks_output[1].raw)

    caption = resume.tasks_output[2].raw

    try:
        publisher = Publisher(access_token=config.access_token)

        # Publish to Instagram
        published_id = publisher.publish(
            image_url=image_generation["image_url"], caption=caption
        )
        print(f"Successfully published to Instagram with ID: {published_id}")
    except Exception as e:
        print(f"Error publishing to Instagram: {e}")


# Ensure this script runs directly
if __name__ == "__main__":
    main()
