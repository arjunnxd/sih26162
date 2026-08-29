"""NASA FIRMS thermal hotspot data source provider.

This provider fetches raw thermal hotspot records from a configurable
FIRMS-compatible HTTP endpoint and returns them in their native FIRMS-style
shape. The shared normalizer is responsible for converting those records into
NormalizedHotspot objects.

No analysis or intelligence logic belongs here.

Configuration:
    FIRMS_API_KEY
        Optional API key. Can also be supplied directly to the provider.

    FIRMS_BASE_URL
        Optional FIRMS-compatible endpoint URL. Can also be supplied directly
        to the provider.

The exact endpoint format may vary depending on the NASA FIRMS API product
being used. This provider therefore keeps the HTTP endpoint configurable and
does not hardcode secrets.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from urllib.request import Request, urlopen

from app.services.data_sources.provider import Provider, ProviderError


class FIRMSProvider(Provider):
    """Provider adapter for configurable NASA FIRMS-compatible endpoints."""

    name = "firms"

    description = (
        "NASA FIRMS-compatible thermal hotspot data provider"
    )

    metadata = {
        "source": "NASA_FIRMS",
        "provider": "firms",
    }

    DEFAULT_TIMEOUT_SECONDS = 20

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("FIRMS_API_KEY")
        self.base_url = base_url or os.getenv("FIRMS_BASE_URL")

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT_SECONDS
        else:
            try:
                self.timeout = float(timeout)
            except (TypeError, ValueError) as exc:
                raise ProviderError(
                    "FIRMS timeout must be a valid number"
                ) from exc

            if self.timeout <= 0:
                raise ProviderError(
                    "FIRMS timeout must be greater than zero"
                )

    def fetch_raw(self, **kwargs: Any) -> list[dict]:
        """Fetch raw FIRMS-style hotspot records.

        Keyword arguments are forwarded as query parameters.

        Supported provider-level keyword arguments:
            - api_key: overrides configured API key
            - timeout: overrides configured timeout
            - url: overrides configured endpoint URL

        Remaining keyword arguments are sent as query parameters.
        """

        api_key = kwargs.pop("api_key", self.api_key)
        url = kwargs.pop("url", self.base_url)
        timeout = kwargs.pop("timeout", self.timeout)

        if not url:
            raise ProviderError(
                "FIRMS endpoint is not configured. "
                "Set FIRMS_BASE_URL or pass base_url/url explicitly."
            )

        try:
            timeout = float(timeout)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                "FIRMS timeout must be a valid number"
            ) from exc

        if timeout <= 0:
            raise ProviderError(
                "FIRMS timeout must be greater than zero"
            )

        request_url = self._build_url(
            url=url,
            api_key=api_key,
            query_params=kwargs,
        )

        request = Request(
            request_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "SIH26162-Thermal-Intelligence-Platform/1.0",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                status_code = getattr(response, "status", 200)

                if status_code < 200 or status_code >= 300:
                    raise ProviderError(
                        f"FIRMS endpoint returned HTTP {status_code}"
                    )

                content = response.read()
                content_type = response.headers.get(
                    "Content-Type",
                    "",
                )

        except HTTPError as exc:
            raise ProviderError(
                f"FIRMS HTTP error: {exc.code} {exc.reason}"
            ) from exc

        except URLError as exc:
            raise ProviderError(
                f"Unable to reach FIRMS endpoint: {exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise ProviderError(
                "FIRMS request timed out"
            ) from exc

        except OSError as exc:
            raise ProviderError(
                f"FIRMS network failure: {exc}"
            ) from exc

        return self._parse_response(content, content_type)

    @staticmethod
    def _build_url(
        *,
        url: str,
        api_key: Optional[str],
        query_params: dict[str, Any],
    ) -> str:
        """Build request URL with optional API key and query parameters."""

        parsed = urlparse(url)

        params = dict(parse_qsl(parsed.query, keep_blank_values=True))

        for key, value in query_params.items():
            if value is None:
                continue

            if isinstance(value, bool):
                params[key] = str(value).lower()
            else:
                params[key] = str(value)

        if api_key and "api_key" not in params:
            params["api_key"] = api_key

        return urlunparse(
            parsed._replace(query=urlencode(params))
        )

    @staticmethod
    def _parse_response(
        content: bytes,
        content_type: str,
    ) -> list[dict]:
        """Parse a JSON FIRMS-compatible response safely."""

        if not content:
            return []

        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProviderError(
                "FIRMS response could not be decoded as UTF-8"
            ) from exc

        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "FIRMS response is not valid JSON"
            ) from exc

        if isinstance(payload, list):
            records = payload

        elif isinstance(payload, dict):
            records = None

            for key in ("data", "records", "hotspots", "features"):
                if key in payload:
                    records = payload[key]
                    break

            if records is None:
                raise ProviderError(
                    "FIRMS JSON response does not contain a supported "
                    "records collection"
                )

        else:
            raise ProviderError(
                "FIRMS response must contain a JSON list or object"
            )

        if not isinstance(records, list):
            raise ProviderError(
                "FIRMS records collection must be a JSON list"
            )

        result: list[dict] = []

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ProviderError(
                    f"FIRMS record at index {index} is not an object"
                )

            result.append(record)

        return result