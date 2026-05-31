"""FastMCP server: Azure DevOps pipeline araclarini MCP "tool" olarak sunar.

Calistirma:
  - stdio (MCP uyumlu istemci / IDE):   `python -m triageops.mcp_server.server`
  - HTTP (orchestrator/uzak istemci):   `MCP_TRANSPORT=streamable-http python -m ...`

Resmi microsoft/azure-devops-mcp server'inda olmayan kritik arac:
  `get_failed_timeline_records` - hangi task'in neden basarisiz oldugunu bulur.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from triageops.ado.builds import BuildReader
from triageops.ado.client import AdoClient
from triageops.ado.writeback import BuildWriter

mcp = FastMCP("triageops")


def _reader() -> BuildReader:
    return BuildReader(AdoClient())


def _writer() -> BuildWriter:
    return BuildWriter(AdoClient())


@mcp.tool()
def list_failed_builds(
    definitions: str | None = None, branch_name: str | None = None, top: int = 10
) -> list[dict[str, Any]]:
    """Son basarisiz build'leri listeler.

    definitions: virgulle ayrilmis pipeline tanim id'leri (opsiyonel).
    branch_name: 'refs/heads/main' gibi dal filtresi (opsiyonel).
    """
    builds = _reader().list_failed_builds(
        definitions=definitions, branch_name=branch_name, top=top
    )
    return [
        {
            "id": b.get("id"),
            "buildNumber": b.get("buildNumber"),
            "definition": (b.get("definition") or {}).get("name"),
            "result": b.get("result"),
            "sourceBranch": b.get("sourceBranch"),
            "finishTime": b.get("finishTime"),
        }
        for b in builds
    ]


@mcp.tool()
def get_build(build_id: int) -> dict[str, Any]:
    """Bir build'in ozet bilgisini dondurur (durum, sonuc, tetikleyen, dal)."""
    b = _reader().get_build(build_id)
    return {
        "id": b.get("id"),
        "buildNumber": b.get("buildNumber"),
        "status": b.get("status"),
        "result": b.get("result"),
        "definition": (b.get("definition") or {}).get("name"),
        "sourceBranch": b.get("sourceBranch"),
        "sourceVersion": b.get("sourceVersion"),
        "requestedFor": (b.get("requestedFor") or {}).get("displayName"),
        "reason": b.get("reason"),
    }


@mcp.tool()
def get_failed_timeline_records(build_id: int) -> list[dict[str, Any]]:
    """Build'in basarisiz task kayitlarini (hata mesajlari + log_id) dondurur.

    Sonuc analizinin baslangic noktasidir: once buradan log_id'leri al,
    sonra get_task_log ile sadece ilgili log'u cek.
    """
    return [r.to_dict() for r in _reader().get_failed_timeline_records(build_id)]


@mcp.tool()
def get_task_log(
    build_id: int,
    log_id: int,
    start_line: int | None = None,
    end_line: int | None = None,
    tail: int | None = 200,
) -> str:
    """Belirli bir task log'unun metnini dondurur (varsayilan: son 200 satir).

    tail=None verilirse tum log; start_line/end_line ile aralik secilebilir.
    """
    return _reader().get_task_log(
        build_id, log_id, start_line=start_line, end_line=end_line, tail=tail
    )


@mcp.tool()
def get_build_changes(build_id: int, top: int = 20) -> list[dict[str, Any]]:
    """Build'e dahil olan commit/degisiklikleri dondurur (regresyon iliskilendirme)."""
    changes = _reader().get_build_changes(build_id, top=top)
    return [
        {
            "id": c.get("id"),
            "message": c.get("message"),
            "author": (c.get("author") or {}).get("displayName"),
            "timestamp": c.get("timestamp"),
        }
        for c in changes
    ]


@mcp.tool()
def list_artifacts(build_id: int) -> list[dict[str, Any]]:
    """Build'in yayinladigi artifact'leri listeler (ad, tip, indirme URL'i, boyut).

    Test sonucu, coverage, build ciktisi gibi artifact'leri analize dahil etmek
    icin kullanilir.
    """
    return _reader().list_artifacts(build_id)


@mcp.tool()
def add_build_tag(build_id: int, tag: str) -> str:
    """Build'e bir tag ekler (orn. 'ai-analyzed')."""
    _writer().add_build_tag(build_id, tag)
    return f"'{tag}' etiketi {build_id} numarali build'e eklendi."


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
