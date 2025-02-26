from crewai import Task


def get_task_description():
    return (
        "Analyser le texte juridique suivant et fournir un résumé court, clair et "
        "accessible aux non-juristes, au format optimisé pour Instagram. Le résumé doit inclure:\n"
        "1. {titre}\n"
        "2. Date de publication: {date_publication}\n"
        "3. Signataires officiels: {signataires}\n"
        "4. Synthèse des principaux points: {contenu}"
    )


def get_expected_output():
    return (
        "Résumé simplifié comprenant : "
        "- Titre du texte juridique, "
        "- Date de publication, "
        "- Signataires, "
        "- Synthèse claire et accessible des principaux points."
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
)
