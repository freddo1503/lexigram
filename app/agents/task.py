from crewai import Task

from app.models.content import Image, Text


def get_task_description():
    return (
        "Analyser le texte juridique fourni et produire un résumé structuré sans omettre d’informations essentielles. "
        "Le résumé doit conserver l’intégralité des éléments clés tout en étant clair et bien organisé. Il doit inclure :\n"
        "1. Titre officiel du texte juridique : {titre}\n"
        "2. Date de publication (format : jour mois année) : {date_publication}\n"
        "3. Signataires officiels : {signataires}\n"
        "4. Synthèse détaillée des principaux points sans altération du contenu : {contenu}"
    )


def get_expected_output():
    return (
        "Un résumé structuré comprenant :\n"
        "- Le titre officiel du texte juridique\n"
        "- La date de publication au format jour mois année\n"
        "- La liste des signataires officiels\n"
        "- Une synthèse détaillée des principaux points, sans omission ni simplification excessive."
    )


text_summary = Task(
    description=get_task_description(),
    expected_output=get_expected_output(),
    agent=None,
)


image_generation = Task(
    description=(
        "Based on the summarized legal text, generate an engaging and visually appealing image "
        "optimized for Instagram. The image should effectively complement the summary, ensuring "
        "clarity and accessibility for a non-expert audience. Do no include any details related "
        "to specific countries, such as flags or country names."
    ),
    expected_output=(
        "A high-quality, visually engaging image that aligns with the summarized legal text. "
        "The design should be clear, professional, and optimized for Instagram, ensuring readability "
        "and accessibility for a general audience. The image must not include country-specific details, "
        "such as flags or country names."
    ),
    context=[text_summary],
    agent=None,
    output_pydantic=Image,
)

caption = Task(
    description=(
        "Convert a detailed legal analysis into a clear and engaging Instagram post. "
        "Ensure the content is concise, easy to understand, and structured for readability. "
        "Do not use bold, italics, asterisks, or any special formatting—just plain text."
    ),
    expected_output=(
        "An Instagram-ready text with key takeaways, bullet points, or a carousel-friendly breakdown. "
        "The content should be legally accurate, engaging, and accessible to a broad audience, formatted strictly in plain text."
    ),
    context=[text_summary],
    agent=None,
    output_pydantic=Text,
    async_execution=False,
)
