from __future__ import annotations

import hashlib
from typing import Optional

import requests
from django.conf import settings
from django.core.cache import cache

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "Exploideo/1.0 (geocoding service)"
DEFAULT_GEOCODING_CACHE_TTL = 86400


def _build_geocoding_query(experience) -> str:
    values = [
        getattr(experience, "location", ""),
        getattr(experience, "city", ""),
        getattr(experience, "island", ""),
        getattr(experience, "province", ""),
        getattr(experience, "region", ""),
        getattr(experience, "country", ""),
    ]

    parts = []
    seen = set()
    for value in values:
        cleaned = (value or "").strip()
        if not cleaned:
            continue

        lowered = cleaned.lower()
        if lowered in seen:
            continue

        seen.add(lowered)
        parts.append(cleaned)

    return ", ".join(parts)


def _normalize_query_for_cache(query: str) -> str:
    # Lowercase and collapse extra whitespace so semantically equal queries share a cache key.
    return " ".join(query.lower().strip().split())


def _cache_key_for_query(query: str) -> str:
    normalized = _normalize_query_for_cache(query)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    return f"geocode:{digest}"


def geocode_experience_location(experience) -> Optional[tuple[float, float]]:
    query = _build_geocoding_query(experience)
    if not query:
        return None

    cache_key = _cache_key_for_query(query)
    try:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        # Cache backend issues must never break geocoding flow.
        pass

    try:
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": "es",
            },
            headers={
                "User-Agent": NOMINATIM_USER_AGENT,
                "Accept-Language": "es",
            },
            timeout=getattr(settings, "GEOCODING_TIMEOUT", 5),
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return None

    if not payload:
        return None

    first = payload[0] if isinstance(payload, list) else None
    if not isinstance(first, dict):
        return None

    lat = first.get("lat")
    lon = first.get("lon")
    if lat is None or lon is None:
        return None

    try:
        coordinates = (float(lat), float(lon))
    except (TypeError, ValueError):
        return None

    try:
        cache.set(
            cache_key,
            coordinates,
            timeout=getattr(settings, "GEOCODING_CACHE_TTL", DEFAULT_GEOCODING_CACHE_TTL),
        )
    except Exception:
        # Cache backend issues must never interrupt the request lifecycle.
        pass

    return coordinates
