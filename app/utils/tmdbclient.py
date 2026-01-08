import os
import logging
import uuid
from typing import Any, Dict, Optional

import requests
from requests import RequestException, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class TMDBError(Exception):
    """Raised when a TMDB upstream call fails in a way the app should handle."""
    def __init__(self, message: str, error_id: str, status_code: Optional[int] = None, body: Optional[str] = None):
        super().__init__(message)
        self.error_id = error_id
        self.status_code = status_code
        self.body = body


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

    def __init__(
        self,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.api_key = api_key or os.getenv("TMDB_API_KEY","c03f10ce149f5b0b162742943632938f")
        self.bearer_token = bearer_token or os.getenv("TMDB_API_BEARER","eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjMDNmMTBjZTE0OWY1YjBiMTYyNzQyOTQzNjMyOTM4ZiIsIm5iZiI6MTc1Nzc1NTcyNi42MzUsInN1YiI6IjY4YzUzOTRlZTUxMmRhZTdlOWE4NWZjYyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.h4-WRZ_j5rYEaqsmXQvD6g7rg9lYV8tUm2geAtrf5aU")
        self.timeout = timeout

        if not self.api_key and not self.bearer_token:
            raise RuntimeError(
                "TMDB credentials not configured. Set TMDB_API_KEY (v3) or TMDB_API_BEARER (v4)."
            )

        # Session with retry/backoff for transient network errors and 5xx upstream statuses
        self.session = Session()
        # Retry on connect/read errors and on certain status codes
        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        params = dict(params or {})
        headers: Dict[str, str] = {}

        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            params["api_key"] = self.api_key

        error_id = uuid.uuid4().hex
        try:
            resp = self.session.request(method, url, params=params, headers=headers, timeout=self.timeout)
            # If we get a non-2xx, capture the body for debugging and raise a TMDBError
            if not resp.ok:
                body = None
                try:
                    body = resp.text
                except Exception:
                    body = "<unavailable>"
                logger.error("TMDB returned non-2xx: status=%s url=%s error_id=%s body=%s", resp.status_code, url, error_id, body)
                raise TMDBError("TMDB returned non-2xx response", error_id=error_id, status_code=resp.status_code, body=body)
            try:
                return resp.json()
            except ValueError:
                # invalid JSON
                body = resp.text if resp is not None else None
                logger.error("TMDB returned invalid JSON: url=%s error_id=%s body=%s", url, error_id, body)
                raise TMDBError("TMDB returned invalid JSON", error_id=error_id, status_code=resp.status_code, body=body)
        except RequestException as exc:
            # Network-level error (connection reset, DNS, timeout, etc.)
            # Log full exception server-side with error_id for correlation
            logger.exception("TMDB request failed: url=%s error_id=%s", url, error_id, exc_info=exc)
            # If the response is present on the exception, try to capture text (best-effort)
            body = None
            resp = getattr(exc, "response", None)
            try:
                if resp is not None:
                    body = resp.text
            except Exception:
                body = None
            raise TMDBError("Failed to fetch from TMDB", error_id=error_id, status_code=getattr(resp, "status_code", None), body=body) from exc

    def search_movies(self, query: str, page: int = 1) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/search/movie",
            params={
                "query": query,
                "page": page,
                "include_adult": False,
            },
        )

    def get_movie_details(self, tmdb_id: int) -> Dict[str, Any]:
        return self._request(
            "GET",
            f"/movie/{tmdb_id}",
            params={
                "append_to_response": "credits,release_dates,spoken_languages",
            },
        )

    @classmethod
    def poster_url(cls, poster_path: Optional[str]) -> Optional[str]:
        if not poster_path:
            return None
        return f"{cls.IMAGE_BASE}{poster_path}"

    @classmethod
    def background_url(cls, backdrop_path: Optional[str]) -> Optional[str]:
        if not backdrop_path:
            return None
        return f"{cls.IMAGE_BASE}{backdrop_path}"


def _extract_certificate(details: Dict[str, Any]) -> Optional[str]:
    results = (details.get("release_dates") or {}).get("results") or []
    preferred_countries = ["US", "GB", "IN"]
    for country in preferred_countries + [r.get("iso_3166_1") for r in results if r.get("iso_3166_1") not in preferred_countries]:
        for r in results:
            if r.get("iso_3166_1") == country:
                for rel in r.get("release_dates", []):
                    cert = (rel or {}).get("certification")
                    if cert:
                        return cert
    return None


def _extract_formats(details: Dict[str, Any]) -> list[str]:
    """
    Extract normalized visual/experience formats from TMDB movie details.

    Normalized tokens returned (lowercase):
      - visual/experience tokens: '2d', '3d', 'imax', '4dx', 'dolby_atmos', 'dolby_vision'

    Notes:
      - This version intentionally omits release-type tokens like 'premiere', 'theatrical', 'theatrical_limited'.
      - We detect visual releases via TMDB release type integers (1..6) but do not add those as tokens.
      - If a visual release exists and no explicit 3D/IMAX was detected, we add '2d' as the default visual token.
    """
    results = (details.get("release_dates") or {}).get("results") or []
    if not results:
        return []

    preferred_countries = ["US", "GB", "IN"]
    formats_set = set()
    seen_countries = set()

    # Types that indicate a visual release (we won't add tokens for these types,
    # but we'll use them to infer that a visual release exists so we can add '2d' if appropriate)
    visual_type_ints = {1, 2, 3, 4, 5, 6}

    def scan_note_for_keywords(note: Optional[str]):
        if not note:
            return
        n = note.lower()
        if "3d" in n or "3-d" in n:
            formats_set.add("3d")
        if "imax" in n:
            formats_set.add("imax")
        if "4dx" in n:
            formats_set.add("4dx")
        # Dolby related checks
        if "dolby" in n:
            if "atmos" in n:
                formats_set.add("dolby_atmos")
            if "vision" in n:
                formats_set.add("dolby_vision")

    # examine preferred countries first, then the rest
    ordered_countries = preferred_countries + [
        r.get("iso_3166_1") for r in results if r.get("iso_3166_1") not in preferred_countries
    ]

    has_visual_release = False

    for country in ordered_countries:
        if not country or country in seen_countries:
            continue
        seen_countries.add(country)
        for r in results:
            if r.get("iso_3166_1") != country:
                continue
            for rel in r.get("release_dates", []):
                # detect visual release presence by type integer
                t = rel.get("type")
                if t in visual_type_ints:
                    has_visual_release = True
                scan_note_for_keywords((rel or {}).get("note"))

    # fallback: scan all release entries if we didn't detect anything in ordered pass
    if not has_visual_release or not formats_set:
        for r in results:
            for rel in r.get("release_dates", []):
                if rel.get("type") in visual_type_ints:
                    has_visual_release = True
                scan_note_for_keywords((rel or {}).get("note"))

    # Add '2d' default if there is at least one visual release and no explicit 3d/imax detected
    if has_visual_release and not any(x in formats_set for x in ("3d", "imax")):
        formats_set.add("2d")

    return sorted(formats_set)


def map_tmdb_to_movie_create(details: Dict[str, Any]) -> Dict[str, Any]:
    imdb_id =details.get("imdb_id")
    title = details.get("title") or details.get("name")
    overview = details.get("overview")
    runtime = details.get("runtime") or 0
    genres = [g.get("name") for g in (details.get("genres") or []) if g.get("name")]
    spoken_langs = [l.get("english_name") or l.get("name") for l in (details.get("spoken_languages") or []) if l.get("english_name") or l.get("name")]
    orig_lang = details.get("original_language")
    background_url = TMDBClient.background_url(details.get("backdrop_path"))
    release_date = details.get("release_date") or None
    vote_average = details.get("vote_average")
    rating = round((vote_average or 0) / 2, 1) if vote_average is not None else None
    certificate = _extract_certificate(details)
    poster_url = TMDBClient.poster_url(details.get("poster_path"))

    # normalized formats like '2d', '3d', 'imax', etc. (no 'premiere'/'theatrical' tokens)
    formats = _extract_formats(details)

    languages = []
    spoken_langs_list = details.get("spoken_languages") or []
    for l in spoken_langs_list:
        name = l.get("english_name") or l.get("name")
        if name and name not in languages:
            languages.append(name)

    # ensure original_language code maps to a full name if present in spoken_languages
    orig_lang = details.get("original_language")
    if orig_lang:
        match = next((s for s in spoken_langs_list if s.get("iso_639_1") == orig_lang), None)
        if match:
            name = match.get("english_name") or match.get("name")
            if name and name not in languages:
                languages.append(name)

    credits = details.get("credits") or {}
    cast_items = credits.get("cast") or []
    crew_items = credits.get("crew") or []

    cast = [
        {
            "name": c.get("name"),
            "character": c.get("character"),
            "order": c.get("order"),
            "profile_path": c.get("profile_path"),
        }
        for c in cast_items[:10]
        if c.get("name")
    ]

    important_jobs = {"Director", "Writer", "Screenplay", "Producer"}
    prioritized = [c for c in crew_items if c.get("job") in important_jobs]
    if len(prioritized) < 10:
        seen = {id(c) for c in prioritized}
        for c in crew_items:
            if id(c) in seen:
                continue
            prioritized.append(c)
            if len(prioritized) >= 10:
                break

    crew = [
        {
            "name": c.get("name"),
            "job": c.get("job"),
            "department": c.get("department"),
            "profile_path": c.get("profile_path"),
        }
        for c in prioritized if c.get("name")
    ][:10]

    # Compatibility: keep 'format' (singular) for legacy DB/schema while using canonical 'formats' (plural)
    return {
        "imdb_id": imdb_id,
        "title": title,
        "description": overview,
        "duration": runtime,
        "genre": genres,
        "language": languages,
        "release_date": release_date,
        "rating": rating,
        "certificate": certificate,
        "poster_url": poster_url,
        "is_active": True,
        "background_image_url": background_url,
        "cast": cast,
        "crew": crew,
        # canonical new field (JSONB array)
        "formats": formats,
        # compatibility field for existing DB column named 'format'
        "format": formats if formats else None,
    }