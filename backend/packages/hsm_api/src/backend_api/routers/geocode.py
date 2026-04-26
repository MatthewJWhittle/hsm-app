"""Public place-search endpoint backed by MapTiler Geocoding."""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend_api.deps.settings_dep import get_settings
from backend_api.schemas_geocode import (
    PlaceSearchCenter,
    PlaceSearchResponse,
    PlaceSearchResult,
)
from hsm_core.settings import Settings

router = APIRouter(prefix="/geocode", tags=["geocode"])

_MAPTILER_GEOCODING_BASE = "https://api.maptiler.com/geocoding"


def _csv_param(value: str) -> str | None:
    cleaned = ",".join(part.strip().lower() for part in value.split(",") if part.strip())
    return cleaned or None


def _finite_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _parse_center(value: object) -> PlaceSearchCenter | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    lng, lat = value
    if not _finite_number(lng) or not _finite_number(lat):
        return None
    if lng < -180 or lng > 180 or lat < -90 or lat > 90:
        return None
    return PlaceSearchCenter(lng=float(lng), lat=float(lat))


def _parse_bbox(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    if not all(_finite_number(item) for item in value):
        return None
    west, south, east, north = (float(item) for item in value)
    if west >= east or south >= north:
        return None
    if west < -180 or east > 180 or south < -90 or north > 90:
        return None
    return (west, south, east, north)


def parse_maptiler_response(payload: Any) -> PlaceSearchResponse:
    if not isinstance(payload, dict):
        return PlaceSearchResponse(results=[])

    attribution = payload.get("attribution")
    if not isinstance(attribution, str):
        attribution = None

    features = payload.get("features")
    if not isinstance(features, list):
        return PlaceSearchResponse(results=[])

    results: list[PlaceSearchResult] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        feature_id = feature.get("id")
        label = feature.get("place_name") or feature.get("matching_place_name") or feature.get("text")
        center = _parse_center(feature.get("center"))
        if not isinstance(feature_id, str) or not isinstance(label, str) or center is None:
            continue

        results.append(
            PlaceSearchResult(
                id=feature_id,
                label=label,
                center=center,
                bbox=_parse_bbox(feature.get("bbox")),
                source="maptiler",
                attribution=attribution,
            )
        )

    return PlaceSearchResponse(results=results)


@router.get("/search", response_model=PlaceSearchResponse)
async def search_places(
    q: Annotated[str, Query(min_length=2, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
    settings: Settings = Depends(get_settings),
) -> PlaceSearchResponse:
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query is too short")

    api_key = (settings.maptiler_api_key or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Place search is not configured.",
        )

    params: dict[str, str | int] = {
        "key": api_key,
        "limit": limit,
        "autocomplete": "true",
    }
    country = _csv_param(settings.geocode_country)
    if country:
        params["country"] = country
    language = _csv_param(settings.geocode_language)
    if language:
        params["language"] = language

    url = f"{_MAPTILER_GEOCODING_BASE}/{quote(query, safe='')}.json"
    try:
        async with httpx.AsyncClient(timeout=settings.geocode_timeout_seconds) as client:
            response = await client.get(url, params=params)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Place search timed out.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Place search is temporarily unavailable.",
        ) from exc

    if response.status_code == 400:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid place-search query.",
        )
    if response.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Place search is not configured.",
        )
    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Place search is temporarily unavailable.",
        )

    return parse_maptiler_response(response.json())
