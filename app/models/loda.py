from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# Model for date ranges used in the request
class DateRange(BaseModel):
    start: date
    end: date


# Request payload model
class RequestPayload(BaseModel):
    sort: str
    legalStatus: List[str]
    pageNumber: int
    natures: List[str]
    secondSort: str
    signatureDate: Optional[DateRange] = None
    pageSize: int
    publicationDate: DateRange


# Model for an individual result item in the response
class ResultItem(BaseModel):
    id: str
    cid: str
    etat: str
    titre: str
    dateDebut: datetime
    dateFin: datetime
    lastUpdate: datetime
    dossiersLegislatifs: List[
        Any
    ]  # Adjust type if you have a specific model for dossiers


# Model for the facet structure found in the response
class Facet(BaseModel):
    facetElem: Optional[Any] = None
    field: str
    values: Dict[str, int]
    childs: Dict[str, Any]
    totalElement: int


# Response payload model
class ResponsePayload(BaseModel):
    executionTime: int
    results: List[ResultItem]
    natures: Facet
    legalStatus: Facet
    totalResultNumber: int
