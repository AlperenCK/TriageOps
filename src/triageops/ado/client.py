"""Azure DevOps REST API icin ince bir httpx istemcisi.

Kimlik dogrulama oncelik sirasi:
  1. Bearer token (pipeline icinde System.AccessToken)  -> Authorization: Bearer
  2. PAT                                                 -> Authorization: Basic base64(":"+PAT)

On-prem (Azure DevOps Server / TFS) ile bulut arasindaki tek fark base URL ve
muhtemelen api-version'dur; ikisi de Settings uzerinden gelir.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from triageops.config import Settings, get_settings


def _auth_header(settings: Settings) -> dict[str, str]:
    if settings.azdo_bearer_token:
        return {"Authorization": f"Bearer {settings.azdo_bearer_token}"}
    if settings.azdo_pat:
        token = base64.b64encode(f":{settings.azdo_pat}".encode()).decode()
        return {"Authorization": f"Basic {token}"}
    return {}


class AdoClient:
    """Proje kapsamindaki Azure DevOps REST cagrilari icin yardimci.

    Senkron httpx kullanir; tum yollar proje temeli (`project_base`) ile
    birlestirilir. `api-version` otomatik eklenir.
    """

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        self._client = client or httpx.Client(
            headers=_auth_header(self.settings),
            verify=self.settings.azdo_verify_ssl,
            timeout=60.0,
        )

    # Dusuk seviye
    def _url(self, path: str, *, collection_scope: bool = False) -> str:
        base = self.settings.collection_base if collection_scope else self.settings.project_base
        return f"{base}/{path.lstrip('/')}"

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        collection_scope: bool = False,
        as_text: bool = False,
    ) -> Any:
        params = {**(params or {}), "api-version": self.settings.azdo_api_version}
        resp = self._client.get(self._url(path, collection_scope=collection_scope), params=params)
        resp.raise_for_status()
        return resp.text if as_text else resp.json()

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        collection_scope: bool = False,
        content_type: str = "application/json",
    ) -> Any:
        params = {**(params or {}), "api-version": self.settings.azdo_api_version}
        resp = self._client.post(
            self._url(path, collection_scope=collection_scope),
            json=json,
            params=params,
            headers={"Content-Type": content_type},
        )
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def put(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        params = {**(params or {}), "api-version": self.settings.azdo_api_version}
        resp = self._client.put(self._url(path), params=params)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AdoClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
