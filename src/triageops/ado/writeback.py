"""Analiz sonucunu Azure DevOps'a geri yazma.

Birincil cikti kanali pipeline Build Summary'dir. Bunun iki yolu var:
  1. Pipeline ICINDE calisiyorsak: `##vso[task.uploadsummary]` logging komutu
     ile bir markdown dosyasi Build Summary sekmesine eklenir. (En temiz yol.)
  2. Pipeline DISINDA (webhook) calisiyorsak: Build Attachments REST API ile
     rapor build'e eklenir, ayrica isaretleme icin tag atilir.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from triageops.ado.client import AdoClient


def emit_build_summary_logging_command(markdown: str, *, title: str = "AI Analizi") -> Path:
    """Markdown'i gecici dosyaya yazip `##vso[task.uploadsummary]` komutunu basar.

    Yalnizca pipeline icinde (TF_BUILD ortaminda) anlamlidir; stdout'a basilan
    logging komutunu Azure Pipelines agent'i yakalar ve Build Summary'ye ekler.
    """
    out_dir = Path(os.getenv("AGENT_TEMPDIRECTORY", os.getenv("BUILD_ARTIFACTSTAGINGDIRECTORY", ".")))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "triageops-summary.md"
    path.write_text(markdown, encoding="utf-8")
    # Azure Pipelines logging komutlari (agent stdout'tan okur):
    print(f"##vso[task.uploadsummary]{path.resolve()}")
    print(f"##[section]{title} olusturuldu")
    return path


def emit_log_issue(message: str, *, kind: str = "warning") -> None:
    """Pipeline log'una bir uyari/hata satiri ekler (Build Summary'de gorunur)."""
    one_line = message.replace("\n", " ").strip()
    print(f"##vso[task.logissue type={kind}]{one_line}")


class BuildWriter:
    """Pipeline disindan (webhook) geri yazma islemleri."""

    def __init__(self, client: AdoClient):
        self.client = client

    def add_build_tag(self, build_id: int, tag: str) -> Any:
        return self.client.put(f"_apis/build/builds/{build_id}/tags/{tag}")

    def upload_attachment(
        self, build_id: int, markdown: str, *, name: str = "triageops-analysis.md"
    ) -> Any:
        """Raporu build'e ek (attachment) olarak yukler.

        Pipeline disindan Build Summary'ye dogrudan yazilamadigi icin rapor
        attachment olarak saklanir ve build 'ai-analyzed' tag'i ile isaretlenir.
        """
        path = f"_apis/build/builds/{build_id}/attachments/triageops/{name}"
        self.client.post(path, json={"content": markdown}, content_type="application/octet-stream")
        return self.add_build_tag(build_id, "ai-analyzed")
