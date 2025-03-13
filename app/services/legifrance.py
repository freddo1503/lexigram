from app.api_client import APIClient
from app.models import loda
from app.models.consult import LegiConsultRequest, LegiConsultResponse


def fetch_legi_consult(
    api_client: APIClient, payload: LegiConsultRequest
) -> LegiConsultResponse:
    """
    Récupère les résultats de consultation pour un texte juridique spécifique via l'API Legifrance.

    Args:
        api_client (APIClient): Instance du client API utilisée pour effectuer la requête.
        payload (LegiConsultRequest): Données de la requête contenant les critères de filtrage.

    Returns:
        LegiConsultResponse: Détails du texte juridique.
    """
    response = api_client.post(
        endpoint="/consult/legiPart",
        payload=payload.model_dump(mode="json", exclude_none=True),
    )

    return LegiConsultResponse.model_validate(response)


def fetch_loda_list(
    api_client: APIClient, payload: loda.RequestPayload
) -> loda.ResponsePayload:
    """
    Récupère la liste des LODA (Lois, Décrets et Arrêtés) depuis l'API Legifrance.

    Args:
        api_client (APIClient): Instance du client API utilisée pour effectuer la requête.
        payload (loda.RequestPayload): Données de la requête spécifiant les filtres de recherche.

    Returns:
        loda.ResponsePayload: Liste des entrées LODA.
    """
    response = api_client.post(
        endpoint="/list/loda", payload=payload.model_dump(mode="json")
    )

    return loda.ResponsePayload.model_validate(response)
