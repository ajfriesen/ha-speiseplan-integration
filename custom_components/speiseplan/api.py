"""HTTP client for the SpeisePlan read-only JSON API (internal/server/api.go)."""

from __future__ import annotations

from typing import Any

import aiohttp


class SpeisePlanError(Exception):
    """Base error talking to SpeisePlan."""


class SpeisePlanConnectionError(SpeisePlanError):
    """SpeisePlan could not be reached."""


def build_base_url(host: str, port: int, use_ssl: bool) -> str:
    """Return the origin SpeisePlan is served from, without a trailing slash."""
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}"


async def async_probe(
    session: aiohttp.ClientSession,
    host: str,
    port: int,
    use_ssl: bool,
) -> dict[str, Any]:
    """Fetch identity from a candidate host.

    The config flow uses this before it has a client, and keys the config entry
    on the returned ``instance_id`` so the entry survives an address change.
    """
    return await SpeisePlanClient(session, host, port, use_ssl).async_get_info()


class SpeisePlanClient:
    """Thin async wrapper over SpeisePlan's /api/v1 endpoints."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        use_ssl: bool = False,
    ) -> None:
        self._session = session
        self.base_url = build_base_url(host, port, use_ssl)
        self._api = f"{self.base_url}/api/v1"

    async def _request(self, path: str) -> Any:
        url = f"{self._api}{path}"
        try:
            async with self._session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise SpeisePlanError(f"HTTP {resp.status}: {text.strip()}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise SpeisePlanConnectionError(str(err)) from err

    async def async_get_info(self) -> dict[str, Any]:
        """Identity, version and the server's idea of today."""
        return await self._request("/info")

    async def async_get_plan(self, days: int) -> dict[str, Any]:
        """The whole planning window: one entry per day, plus staged leftovers."""
        return await self._request(f"/plan?days={days}")
