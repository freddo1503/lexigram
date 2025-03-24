import logging

from app.api_client import LegifranceApiClient
from app.models import loda
from app.models.consult import LegiConsultRequest, LegiConsultResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_legi_consult(
    api_client: LegifranceApiClient, payload: LegiConsultRequest
) -> LegiConsultResponse:
    """
    Récupère les résultats de consultation pour un texte juridique spécifique via l'API Legifrance.

    Args:
        api_client (LegifranceApiClient): Instance du client API utilisée pour effectuer la requête.
        payload (LegiConsultRequest): Données de la requête contenant les critères de filtrage.

    Returns:
        LegiConsultResponse: Détails du texte juridique.
    """

    logger.info(
        "Sending payload: %s", payload.model_dump(mode="json", exclude_none=True)
    )

    response = api_client.post(
        endpoint="/consult/legiPart",
        payload=payload.model_dump(mode="json", exclude_none=True),
    )

    return LegiConsultResponse.model_validate(response)


def fetch_loda_list(
    api_client: LegifranceApiClient, payload: loda.RequestPayload
) -> loda.ResponsePayload:
    """
    Récupère la liste des LODA (Lois, Décrets et Arrêtés) depuis l'API Legifrance.

    Args:
        api_client (LegifranceApiClient): Instance du client API utilisée pour effectuer la requête.
        payload (loda.RequestPayload): Données de la requête spécifiant les filtres de recherche.

    Returns:
        loda.ResponsePayload: Liste des entrées LODA.
    """
    response = api_client.post(
        endpoint="/list/loda", payload=payload.model_dump(mode="json")
    )

    return loda.ResponsePayload.model_validate(response)
