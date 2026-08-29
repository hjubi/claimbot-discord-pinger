"""Thin async HTTP client for the TibiaClaims API."""

from __future__ import annotations

import logging

import aiohttp

from .models import Board

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)


class TibiaClaimsApiError(RuntimeError):
    """Raised when the API cannot be reached or returns an unexpected payload."""


class TibiaClaimsClient:
    """Fetches and parses the claim-servers board endpoint."""

    def __init__(self, url: str, session: aiohttp.ClientSession) -> None:
        self._url = url
        self._session = session

    async def fetch_raw(self) -> dict:
        """Fetch and return the raw, unparsed JSON payload."""
        try:
            async with self._session.get(self._url, timeout=_REQUEST_TIMEOUT) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise TibiaClaimsApiError(
                        f"Unexpected status {resp.status} from {self._url}: {body[:200]}"
                    )
                return await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise TibiaClaimsApiError(f"Network error while fetching {self._url}: {exc}") from exc

    async def fetch_board(self) -> tuple[Board, dict]:
        """Fetch the board and return both the parsed model and raw payload."""
        payload = await self.fetch_raw()
        try:
            return Board.from_dict(payload), payload
        except (KeyError, TypeError) as exc:
            raise TibiaClaimsApiError(f"Malformed payload from {self._url}: {exc}") from exc
