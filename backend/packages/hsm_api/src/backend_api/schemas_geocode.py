"""Schemas for public place-search responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlaceSearchCenter(BaseModel):
    lng: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


class PlaceSearchResult(BaseModel):
    id: str
    label: str
    center: PlaceSearchCenter
    bbox: tuple[float, float, float, float] | None = None
    source: str
    attribution: str | None = None


class PlaceSearchResponse(BaseModel):
    results: list[PlaceSearchResult]
