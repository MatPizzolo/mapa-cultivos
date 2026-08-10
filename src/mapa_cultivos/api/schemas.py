"""Pydantic models for the /clasificar contract (SPEC §6)."""

from typing import Literal

from pydantic import BaseModel, Field

Modelo = Literal["clasicas-rf", "clasicas-knn", "embeddings-rf", "embeddings-knn"]


class ClasificarRequest(BaseModel):
    geometry: dict = Field(description="GeoJSON Polygon, hasta 5.000 ha, dentro de Argentina")
    campania: str = Field(pattern=r"^\d{4}-\d{2}$", examples=["2024-25"])
    modelo: Modelo


class ClaseArea(BaseModel):
    codigo: int
    clase: str
    ha: float
    pct: float


class ClasificarResponse(BaseModel):
    clases: list[ClaseArea]
    area_total_ha: float
    advertencia: str = "Clasificación en vivo, no validada."
