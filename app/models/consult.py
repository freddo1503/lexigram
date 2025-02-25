from datetime import date as dt_date
from typing import List, Optional

from pydantic import BaseModel, Field


class LegiConsultRequest(BaseModel):
    searchedString: Optional[str] = Field(
        default=None,
        description="Texte de la recherche ayant aboutie à la consultation du texte",
    )
    date: dt_date = Field(
        ...,
        description="Date de consultation",
    )
    textId: str = Field(
        ...,
        description="Chronical ID du texte",
    )


class Article(BaseModel):
    id: str
    cid: str
    intOrdre: int
    etat: str
    num: str
    path: str
    content: Optional[str]


class LegiConsultResponse(BaseModel):
    executionTime: int
    dereferenced: bool
    id: str
    cid: str
    title: str
    nor: Optional[str]
    jorfText: Optional[str]
    jurisState: Optional[str]
    modifDate: Optional[dt_date]
    jurisDate: Optional[dt_date]
    dateDebutVersion: Optional[dt_date]
    dateFinVersion: Optional[dt_date]
    signers: Optional[str]
    prepWork: Optional[str]
    dateParution: Optional[int]
    numParution: Optional[str]
    nature: Optional[str]
    articles: List[Article]
