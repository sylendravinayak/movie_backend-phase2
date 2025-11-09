import os
from typing import Any, Dict, List, Optional

import requests


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

    def __init__(
        self,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("TMDB_API_KEY","c03f10ce149f5b0b162742943632938f")
        self.bearer_token = bearer_token or os.getenv("TMDB_API_BEARER","eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjMDNmMTBjZTE0OWY1YjBiMTYyNzQyOTQzNjMyOTM4ZiIsIm5iZiI6MTc1Nzc1NTcyNi42MzUsInN1YiI6IjY4YzUzOTRlZTUxMmRhZTdlOWE4NWZjYyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.h4-WRZ_j5rYEaqsmXQvD6g7rg9lYV8tUm2geAtrf5aU")
        self.timeout = timeout

        if not self.api_key and not self.bearer_token:
            raise RuntimeError(
                "TMDB credentials not configured. Set TMDB_API_KEY (v3) or TMDB_API_BEARER (v4)."
            )

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        params = dict(params or {})
        headers: Dict[str, str] = {}

        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            params["api_key"] = self.api_key

        resp = requests.request(method, url, params=params, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

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
        # credits for cast/crew, release_dates for certificate, spoken_languages included
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
    # prioritize preferred countries, fall back to any with certification
    for country in preferred_countries + [r.get("iso_3166_1") for r in results if r.get("iso_3166_1") not in preferred_countries]:
        for r in results:
            if r.get("iso_3166_1") == country:
                for rel in r.get("release_dates", []):
                    cert = (rel or {}).get("certification")
                    if cert:
                        return cert
    return None


def map_tmdb_to_movie_create(details: Dict[str, Any]) -> Dict[str, Any]:
    # Map TMDB fields to your MovieCreate schema
    title = details.get("title") or details.get("name")
    overview = details.get("overview")
    runtime = details.get("runtime") or 0
    genres = [g.get("name") for g in (details.get("genres") or []) if g.get("name")]
    # languages: use spoken language names; include original_language code if present
    spoken_langs = [l.get("english_name") or l.get("name") for l in (details.get("spoken_languages") or []) if l.get("english_name") or l.get("name")]
    orig_lang = details.get("original_language")
    languages = list({*(spoken_langs or []), *( [orig_lang] if orig_lang else [] )})
    background_url = TMDBClient.background_url(details.get("backdrop_path"))
    release_date = details.get("release_date") or None
    vote_average = details.get("vote_average")
    rating = round((vote_average or 0) / 2, 1) if vote_average is not None else None  # Convert 0-10 to ~0-5
    certificate = _extract_certificate(details)
    poster_url = TMDBClient.poster_url(details.get("poster_path"))

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
    # Prefer directors/writers/producers in crew
    important_jobs = {"Director", "Writer", "Screenplay", "Producer"}
    prioritized = [c for c in crew_items if c.get("job") in important_jobs]
    if len(prioritized) < 10:
        # fill up to 10
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

    return {
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
    }