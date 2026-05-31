"""Ajan icin arac tanimlari (OpenAI tool-calling formati) ve calistirici.

Bu modul, MCP server'daki araclarin AYNISINI yerel LLM'in dogrudan
kullanabilecegi OpenAI 'tools' semasi olarak sunar ve cagrilari ADO katmanina
yonlendirir. Boylece otomatik akis (CLI/webhook) ek bir subprocess'e gerek
duymadan ayni ADO mantigini kullanir; MCP server ise interaktif (IDE)
kullanim icin ayni araclari MCP transport uzerinden sunmaya devam eder.
"""

from __future__ import annotations

import json
from typing import Any

from devops_agent.ado.builds import BuildReader
from devops_agent.ado.client import AdoClient

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_failed_timeline_records",
            "description": "Build'in basarisiz task kayitlarini (hata mesajlari + log_id) dondurur. Analize buradan basla.",
            "parameters": {
                "type": "object",
                "properties": {"build_id": {"type": "integer"}},
                "required": ["build_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_log",
            "description": "Belirli bir task log'unun metnini dondurur (varsayilan son 200 satir).",
            "parameters": {
                "type": "object",
                "properties": {
                    "build_id": {"type": "integer"},
                    "log_id": {"type": "integer"},
                    "tail": {"type": "integer", "description": "Son N satir; tum log icin null"},
                },
                "required": ["build_id", "log_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_build_changes",
            "description": "Build'e dahil commit/degisiklikleri dondurur (regresyon iliskilendirme).",
            "parameters": {
                "type": "object",
                "properties": {"build_id": {"type": "integer"}, "top": {"type": "integer"}},
                "required": ["build_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_artifacts",
            "description": "Build'in yayinladigi artifact'leri (test sonucu/coverage/build ciktisi) listeler: ad, tip, indirme URL'i, boyut.",
            "parameters": {
                "type": "object",
                "properties": {"build_id": {"type": "integer"}},
                "required": ["build_id"],
            },
        },
    },
]


class ToolExecutor:
    """LLM'in cagirdigi araci ADO katmanindaki gercek fonksiyona yonlendirir."""

    def __init__(self, reader: BuildReader | None = None):
        self.reader = reader or BuildReader(AdoClient())

    def call(self, name: str, args: dict[str, Any]) -> str:
        if name == "get_failed_timeline_records":
            records = self.reader.get_failed_timeline_records(int(args["build_id"]))
            return json.dumps([r.to_dict() for r in records], ensure_ascii=False)
        if name == "get_task_log":
            return self.reader.get_task_log(
                int(args["build_id"]),
                int(args["log_id"]),
                tail=args.get("tail", 200),
            )
        if name == "get_build_changes":
            changes = self.reader.get_build_changes(
                int(args["build_id"]), top=int(args.get("top", 20))
            )
            return json.dumps(changes, ensure_ascii=False)
        if name == "list_artifacts":
            artifacts = self.reader.list_artifacts(int(args["build_id"]))
            return json.dumps(artifacts, ensure_ascii=False)
        return json.dumps({"error": f"bilinmeyen arac: {name}"}, ensure_ascii=False)
