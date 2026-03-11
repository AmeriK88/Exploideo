from __future__ import annotations

import hashlib
import time
from typing import Optional

import requests
from django.conf import settings
from django.core.cache import cache

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_GEOCODING_CACHE_TTL = 86400


def _build_geocoding_query(experience) -> str:
    values = [
        getattr(experience, "city", ""),
        getattr(experience, "island", ""),
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
    return " ".join(query.lower().strip().split())


def _cache_key_for_query(query: str) -> str:
    normalized = _normalize_query_for_cache(query)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    return f"geocode:{digest}"


def _respect_nominatim_rate_limit():
    """
    Ensure at least ~1 second between Nominatim requests.
    """
    key = "nominatim:last_request"

    try:
        last = cache.get(key)
        now = time.time()

        if last:
            diff = now - last
            if diff < 1:
                time.sleep(1 - diff)

        cache.set(key, time.time(), timeout=2)
    except Exception:
        pass


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
        pass

    try:
        _respect_nominatim_rate_limit()

        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": "es",
                "addressdetails": 0,
            },
            headers={
                "User-Agent": getattr(
                    settings,
                    "NOMINATIM_USER_AGENT",
                    "Exploideo/1.0 (contact@exploideo.com)",
                ),
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
            timeout=getattr(
                settings,
                "GEOCODING_CACHE_TTL",
                DEFAULT_GEOCODING_CACHE_TTL,
            ),
        )
    except Exception:
        pass

    return coordinates