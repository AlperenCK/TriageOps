"""Webhook tetikleyici — Azure DevOps Service Hook alicisi (FastAPI).

Service Hook olaylari:
  - Klasik:        publisherId=tfs, eventType=build.complete  (buildStatus=Failed)
  - YAML pipeline: ms.vss-pipelines.run-state-changed-event   (runResultId=Failed)

Abonelik kurulumu (On-prem/bulut), Project Settings > Service Hooks veya
POST {collection}/_apis/hooks/subscriptions ile yapilir; consumer 'webHooks',
url bu servisin /hook endpoint'i olur.

Calistirma:  uvicorn triageops.triggers.webhook:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from triageops.ado.builds import BuildReader
from triageops.ado.client import AdoClient
from triageops.ado.writeback import BuildWriter
from triageops.agent.orchestrator import Orchestrator
from triageops.config import get_settings
from triageops.report import build_report

logger = logging.getLogger("triageops.webhook")
app = FastAPI(title="TriageOps Webhook")


def extract_build_id(payload: dict[str, Any]) -> int | None:
    """Hem build.complete hem run-state-changed payload'larindan build/run id cikarir."""
    resource = payload.get("resource") or {}

    # Klasik build.complete: resource.id veya resource.buildId
    for key in ("id", "buildId"):
        if isinstance(resource.get(key), int):
            return resource[key]

    # YAML pipeline run-state-changed: resource.run.id
    run = resource.get("run") or {}
    if isinstance(run.get("id"), int):
        return run["id"]

    return None


def is_failure(payload: dict[str, Any]) -> bool:
    resource = payload.get("resource") or {}
    if resource.get("result") == "failed":
        return True
    run = resource.get("run") or {}
    return run.get("result") == "failed"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/hook")
async def hook(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    settings = get_settings()

    if settings.webhook_secret:
        token = request.query_params.get("token")
        if token != settings.webhook_secret and authorization != f"Basic {settings.webhook_secret}":
            raise HTTPException(status_code=401, detail="gecersiz secret")

    payload = await request.json()

    if not is_failure(payload):
        return {"status": "skipped", "reason": "basarisizlik degil"}

    build_id = extract_build_id(payload)
    if build_id is None:
        raise HTTPException(status_code=400, detail="build id bulunamadi")

    logger.info("Build %s icin analiz baslatiliyor", build_id)
    reader = BuildReader(AdoClient(settings))
    try:
        b = reader.get_build(build_id)
        summary = f"definition={b.get('definition', {}).get('name')} branch={b.get('sourceBranch')}"
        build_url = (b.get("_links", {}).get("web", {}) or {}).get("href")
    except Exception:  # noqa: BLE001
        summary, build_url = None, None

    result = Orchestrator(settings=settings).analyze(build_id, build_summary=summary)
    report = build_report(result, build_url=build_url)

    # Pipeline disindayiz: raporu attachment olarak yukle + tag ata.
    try:
        BuildWriter(AdoClient(settings)).upload_attachment(build_id, report)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geri yazma basarisiz: %s", exc)

    return {"status": "analyzed", "build_id": build_id, "tool_calls": result.tool_calls}
