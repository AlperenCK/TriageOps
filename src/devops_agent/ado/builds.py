"""Build / pipeline okuma islemleri.

En kritik fonksiyon `get_failed_timeline_records`: bir build'in timeline'ini
cekip yalnizca BASARISIZ task kayitlarini (hata mesajlari + log id'leri ile)
dondurur. Bu sayede tum loglari indirmek yerine sadece ilgili task log'unu
cekebiliriz; hem teshis dogrulugu hem de LLM context boyutu icin kritiktir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from devops_agent.ado.client import AdoClient


@dataclass
class FailedRecord:
    """Timeline icindeki basarisiz bir kaydi (genelde Task) temsil eder."""

    record_id: str
    name: str
    record_type: str
    result: str
    log_id: int | None
    issues: list[str] = field(default_factory=list)
    parent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "name": self.name,
            "type": self.record_type,
            "result": self.result,
            "log_id": self.log_id,
            "issues": self.issues,
            "parent_id": self.parent_id,
        }


class BuildReader:
    def __init__(self, client: AdoClient):
        self.client = client

    # ── Build listeleme / detay ─────────────────────────────────────
    def list_failed_builds(
        self,
        *,
        definitions: str | None = None,
        branch_name: str | None = None,
        top: int = 10,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "statusFilter": "completed",
            "resultFilter": "failed",
            "$top": top,
            "queryOrder": "finishTimeDescending",
        }
        if definitions:
            params["definitions"] = definitions
        if branch_name:
            params["branchName"] = branch_name
        data = self.client.get("_apis/build/builds", params=params)
        return data.get("value", [])

    def get_build(self, build_id: int) -> dict[str, Any]:
        return self.client.get(f"_apis/build/builds/{build_id}")

    def get_build_changes(self, build_id: int, top: int = 20) -> list[dict[str, Any]]:
        data = self.client.get(
            f"_apis/build/builds/{build_id}/changes", params={"$top": top}
        )
        return data.get("value", [])

    # ── Timeline -> basarisiz kayitlar ──────────────────────────────
    def get_timeline(self, build_id: int) -> dict[str, Any]:
        return self.client.get(f"_apis/build/builds/{build_id}/timeline")

    def get_failed_timeline_records(self, build_id: int) -> list[FailedRecord]:
        """Timeline'dan basarisiz kayitlari cikarir.

        Oncelik Task tipindeki kayitlardir (gercek hatanin oldugu yer); ancak
        hicbir Task 'failed' degilse (orn. job seviyesinde iptal/timeout)
        failed olan diger kayitlar da dondurulur.
        """
        timeline = self.get_timeline(build_id)
        records = timeline.get("records", [])

        failed = [r for r in records if r.get("result") == "failed"]
        tasks = [r for r in failed if r.get("type") == "Task"]
        chosen = tasks if tasks else failed

        result: list[FailedRecord] = []
        for r in chosen:
            issues = [
                i.get("message", "")
                for i in (r.get("issues") or [])
                if i.get("type") == "error"
            ]
            log = r.get("log") or {}
            result.append(
                FailedRecord(
                    record_id=r.get("id", ""),
                    name=r.get("name", ""),
                    record_type=r.get("type", ""),
                    result=r.get("result", ""),
                    log_id=log.get("id"),
                    issues=issues,
                    parent_id=r.get("parentId"),
                )
            )
        return result

    # ── Log icerigi ─────────────────────────────────────────────────
    def get_task_log(
        self,
        build_id: int,
        log_id: int,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
        tail: int | None = None,
    ) -> str:
        """Belirli bir log'un metnini dondurur.

        `tail` verilirse log'un yalnizca son N satiri dondurulur (hata
        genelde sonda olur ve context'i kucuk tutar). `start_line`/`end_line`
        dogrudan API'ye gecirilir.
        """
        params: dict[str, Any] = {}
        if start_line is not None:
            params["startLine"] = start_line
        if end_line is not None:
            params["endLine"] = end_line
        text = self.client.get(
            f"_apis/build/builds/{build_id}/logs/{log_id}",
            params=params or None,
            as_text=True,
        )
        if tail is not None:
            lines = text.splitlines()
            text = "\n".join(lines[-tail:])
        return text
