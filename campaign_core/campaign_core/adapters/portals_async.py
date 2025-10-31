# campaign_core/adapters/portals_async.py
from __future__ import annotations
import asyncio
import httpx
from typing import Dict
import backoff
import logging

logger = logging.getLogger(__name__)

class PortalsAsync:
    def __init__(self, base_urls: Dict[str, str], creds: tuple[str, str], *,
                 concurrency: int = 8, timeout_s: float = 30.0, retries: int = 3):
        self._sem = asyncio.Semaphore(concurrency)
        self._client = httpx.AsyncClient(
            timeout=timeout_s,
            limits=httpx.Limits(max_connections=concurrency,
                                 max_keepalive_connections=concurrency),
            auth=httpx.BasicAuth(creds[0], creds[1]),
        )
        self._base = base_urls  # key -> url
        self._retries = retries
        logger.info("portals_async_initialized", concurrency=concurrency, retries=retries, portals=len(base_urls))

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException),
        max_tries=lambda self: self._retries + 1,
        giveup=lambda e: isinstance(e, httpx.HTTPStatusError) and e.response.status_code not in (429, 500, 502, 503, 504)
    )
    async def _get(self, key: str, path: str):
        async with self._sem:
            url = self._base[key].rstrip('/') + '/' + path.lstrip('/')
            r = await self._client.get(url)
            r.raise_for_status()
            return r.json()

    async def fetch_subjects(self, key: str, activity_id: str) -> dict:
        return await self._get(key, f"activities/{activity_id}/subjects")

    async def get_jobs(self, key: str, status: str = "webshop (selling)") -> list[dict]:
        """Fetch jobs with given status"""
        return await self._get(key, f"jobs?status={status}")

    async def get_activities_for_job(self, key: str, job_id: str) -> list[dict]:
        """Get activities for a job"""
        return await self._get(key, f"jobs/{job_id}/activities")

    async def get_subject(self, key: str, subject_id: str) -> dict:
        """Get subject details"""
        return await self._get(key, f"subjects/{subject_id}")