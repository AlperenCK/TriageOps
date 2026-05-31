"""Uygulama konfigurasyonu.

Tum ayarlar ortam degiskenlerinden (veya .env dosyasindan) okunur.
Hem Azure DevOps Services (bulut) hem de Azure DevOps Server / TFS (on-prem)
desteklenir; tek fark `AZDO_BASE_URL` ve muhtemelen `AZDO_API_VERSION`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure DevOps
    # Bulut:   https://dev.azure.com/<org>
    # On-prem: https://tfs.sirket.local/DefaultCollection
    azdo_base_url: str = Field(default="https://dev.azure.com/org")
    azdo_project: str = Field(default="project")
    azdo_pat: str = Field(default="")
    # Pipeline icinden System.AccessToken; doldurulursa PAT'in onune gecer.
    azdo_bearer_token: str = Field(default="")
    azdo_api_version: str = Field(default="7.1")
    azdo_verify_ssl: bool = Field(default=True)

    # Yerel LLM (OpenAI uyumlu)
    llm_base_url: str = Field(default="http://localhost:11434/v1")
    llm_model: str = Field(default="qwen2.5-coder:14b")
    llm_api_key: str = Field(default="not-needed")
    llm_max_tool_iterations: int = Field(default=8)

    # Webhook
    webhook_secret: str = Field(default="")

    @property
    def project_base(self) -> str:
        """Proje kapsamindaki REST cagrilarinin temel URL'i."""
        return f"{self.azdo_base_url.rstrip('/')}/{self.azdo_project}"

    @property
    def collection_base(self) -> str:
        """Koleksiyon/organizasyon kapsamindaki cagrilarin temel URL'i.

        (Service Hook abonelikleri gibi proje-ustu kaynaklar icin.)
        """
        return self.azdo_base_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Tekil Settings ornegi dondurur (process boyunca cache'lenir)."""
    return Settings()
