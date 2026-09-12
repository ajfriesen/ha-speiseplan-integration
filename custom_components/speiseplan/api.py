"""HTTP client for the SpeisePlan read-only JSON API (internal/server/api.go)."""

from __future__ import annotations

from typing import Any

import aiohttp


class SpeisePlanError(Exception):
    """Base error talking to SpeisePlan."""


class SpeisePlanAuthError(SpeisePlanError):
    """The API token was rejected (HTTP 401)."""


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
    token: str,
) -> dict[str, Any]:
    """Fetch identity from a candidate host, validating the token on the way.

    The config flow uses this before it has a client, and keys the config entry
    on the returned ``instance_id`` so the entry survives an address change.
    """
    return await SpeisePlanClient(session, host, port, token, use_ssl).async_get_info()


class SpeisePlanClient:
    """Thin async wrapper over SpeisePlan's /api/v1 endpoints."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str,
        use_ssl: bool = False,
    ) -> None:
        self._session = session
        self.base_url = build_base_url(host, port, use_ssl)
        self._api = f"{self.base_url}/api/v1"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, path: str) -> Any:
        url = f"{self._api}{path}"
        try:
            async with self._session.get(
                url,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise SpeisePlanAuthError("invalid API token")
                if resp.status >= 400:
                    text = await resp.text()
                    raise SpeisePlanError(f"HTTP {resp.status}: {text.strip()}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise SpeisePlanConnectionError(str(err)) from err

    async def async_get_info(self) -> dict[str, Any]:
        """Identity, version and the server's idea of today. Validates the token."""
        return await self._request("/info")

    async def async_get_plan(self, days: int) -> dict[str, Any]:
        """The whole planning window: one entry per day, plus staged leftovers."""
        return await self._request(f"/plan?days={days}")

    async def async_get_photo(self, recipe_id: int) -> tuple[bytes, str]:
        """Fetch a recipe photo as (bytes, content_type).

        SpeisePlan serves both locally stored and externally hosted photos from
        this one authenticated endpoint, so the token never reaches a third-party
        host and Home Assistant never fetches a URL somebody pasted into a recipe.
        """
        url = f"{self._api}/recipes/{recipe_id}/photo"
        try:
            async with self._session.get(
                url,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 401:
                    raise SpeisePlanAuthError("invalid API token")
                if resp.status >= 400:
                    raise SpeisePlanError(f"HTTP {resp.status} fetching photo")
                content_type = (resp.content_type or "").strip()
                if not content_type.startswith("image/"):
                    raise SpeisePlanError(f"not an image: {content_type!r}")
                return await resp.read(), content_type
        except aiohttp.ClientError as err:
            raise SpeisePlanConnectionError(str(err)) from err
