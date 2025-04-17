import logging

from app.api_client import LegifranceApiClient
from app.errors.exceptions import (
    DataIntegrityError,
    DataParsingError,
    LegifranceError,
)
from app.errors.handlers import retry
from app.models import loda
from app.models.consult import LegiConsultRequest, LegiConsultResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@retry(max_attempts=3)
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

    Raises:
        LegifranceError: En cas d'erreur lors de la communication avec l'API Legifrance.
        DataParsingError: Si la réponse ne peut pas être analysée correctement.
    """
    try:
        logger.info(
            "Sending payload to Legifrance API: %s",
            payload.model_dump(mode="json", exclude_none=True),
        )

        response = api_client.post(
            endpoint="/consult/legiPart",
            payload=payload.model_dump(mode="json", exclude_none=True),
        )

        try:
            return LegiConsultResponse.model_validate(response)
        except Exception as e:
            raise DataParsingError(
                f"Failed to parse Legifrance consultation response: {str(e)}",
                original_exception=e,
                details={"response": response},
            )
    except Exception as e:
        if not isinstance(e, (LegifranceError, DataParsingError)):
            raise LegifranceError(
                f"Error fetching consultation from Legifrance: {str(e)}",
                original_exception=e,
            ) from e
        raise


@retry(max_attempts=3)
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

    Raises:
        LegifranceError: En cas d'erreur lors de la communication avec l'API Legifrance.
        DataParsingError: Si la réponse ne peut pas être analysée correctement.
    """
    try:
        logger.info(
            "Fetching LODA list from Legifrance API with filters: %s",
            payload.model_dump(mode="json"),
        )

        response = api_client.post(
            endpoint="/list/loda", payload=payload.model_dump(mode="json")
        )

        try:
            return loda.ResponsePayload.model_validate(response)
        except Exception as e:
            raise DataParsingError(
                f"Failed to parse Legifrance LODA list response: {str(e)}",
                original_exception=e,
                details={"response": response},
            )
    except Exception as e:
        if not isinstance(e, (LegifranceError, DataParsingError)):
            raise LegifranceError(
                f"Error fetching LODA list from Legifrance: {str(e)}",
                original_exception=e,
            ) from e
        raise


def extract_legifrance_url(
    response: LegiConsultResponse, doc_type: str = "jorf"
) -> str:
    """
    Build l'URL publique Legifrance d'une réponse de consultation.

    Args:
        response (LegiConsultResponse): Réponse contenant les métadonnées du texte juridique.
        doc_type (str): Type de document ("loda", "jorf", etc.). Par défaut "jorf".

    Returns:
        str: URL publique vers le texte juridique sur Legifrance.

    Raises:
        DataIntegrityError: Si l'identifiant du contenu est introuvable.
    """
    cid = getattr(response, "cid", None)
    if not cid:
        raise DataIntegrityError(
            "Identifiant 'cid' introuvable dans la réponse Legifrance",
            details={
                "response_type": type(response).__name__,
                "available_attrs": dir(response),
            },
        )

    url = f"https://www.legifrance.gouv.fr/{doc_type}/id/{cid}"
    logger.debug("Generated Legifrance URL: %s", url)
    return url
