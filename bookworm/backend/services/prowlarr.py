import os
from typing import List, Dict, Any

import httpx


def _get_config():
    url = os.getenv("PROWLARR_URL", "").rstrip("/")
    key = os.getenv("PROWLARR_API_KEY", "")
    return url, key


def _client(url: str, key: str) -> httpx.AsyncClient:
    headers = {"X-Api-Key": key} if key else {}
    return httpx.AsyncClient(base_url=url, headers=headers, timeout=15.0)


async def search(query: str) -> List[Dict[str, Any]]:
    url, key = _get_config()
    if not url:
        raise RuntimeError("Prowlarr is not configured. Set PROWLARR_URL and PROWLARR_API_KEY.")
    async with _client(url, key) as client:
        resp = await client.get(
            "/api/v1/search",
            params={"query": query, "categories": [7000, 7020]},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data:
        results.append({
            "guid": item.get("guid"),
            "title": item.get("title"),
            "indexer": item.get("indexer"),
            "indexer_id": item.get("indexerId"),
            "size": item.get("size"),
            "seeders": item.get("seeders"),
            "leechers": item.get("leechers"),
            "download_url": item.get("downloadUrl"),
            "info_url": item.get("infoUrl"),
            "publish_date": item.get("publishDate"),
        })
    return results


async def download(guid: str, indexer_id: int) -> Dict[str, Any]:
    url, key = _get_config()
    if not url:
        raise RuntimeError("Prowlarr is not configured.")
    async with _client(url, key) as client:
        resp = await client.post(
            "/api/v1/search",
            json={"guid": guid, "indexerId": indexer_id},
        )
        resp.raise_for_status()
        return resp.json()
