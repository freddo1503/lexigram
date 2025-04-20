from datetime import date

import pytest

from app.errors.exceptions import DataIntegrityError
from app.models.consult import Article, LegiConsultResponse
from app.services.legifrance import extract_legifrance_url


def get_sample_legiconsult_response() -> LegiConsultResponse:
    return LegiConsultResponse(
        executionTime=9,
        dereferenced=False,
        id="LEGITEXT000051187583_19-02-2025",
        cid="JORFTEXT000051186804",
        title="LOI n° 2025-140 du 17 février 2025 autorisant l'approbation de l'accord entre la France et l'Allemagne",
        nor="EAEJ2402927L",
        jorfText="JORF n°0041 du 18 février 2025",
        jurisState="Vigueur",
        modifDate=date(2025, 2, 19),
        jurisDate=date(2025, 2, 19),
        dateDebutVersion=date(2025, 2, 19),
        dateFinVersion=date(2999, 1, 1),
        signers="<p>La présente loi sera exécutée comme loi de l'Etat...</p>",
        prepWork="<p>Travaux préparatoires...</p>",
        dateParution=1739836800000,
        numParution="0041",
        nature="LOI",
        articles=[
            Article(
                id="LEGIARTI000051187584",
                cid="JORFARTI000051186805",
                intOrdre=524287,
                etat="VIGUEUR",
                num="unique",
                path="/LEGIARTI000051187584",
                content="<p>Est autorisée l'approbation de l'accord...</p>",
            )
        ],
    )


def test_extract_legifrance_url_success():
    response = get_sample_legiconsult_response()
    url = extract_legifrance_url(response)
    assert url == "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051186804"


def test_extract_legifrance_url_custom_doc_type():
    response = get_sample_legiconsult_response()
    url = extract_legifrance_url(response, doc_type="loda")
    assert url == "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000051186804"


def test_extract_legifrance_url_missing_cid():
    response = get_sample_legiconsult_response()
    response.cid = None
    with pytest.raises(
        DataIntegrityError,
        match="Identifiant 'cid' introuvable dans la réponse Legifrance",
    ):
        extract_legifrance_url(response)
