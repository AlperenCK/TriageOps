"""Ajan dongusu: yerel LLM + arac cagirma (tool-calling).

LLM bir basarisiz build'i analiz eder; araclari (timeline, log, changes) cagirir
ve sonunda markdown bir teshis/cozum raporu uretir. Dongu, arac cagrisi kalmayana
veya azami iterasyona ulasilana kadar surer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from triageops.agent.prompts import SYSTEM_PROMPT, build_user_task
from triageops.agent.tools import TOOL_SCHEMAS, ToolExecutor
from triageops.config import Settings, get_settings
from triageops.llm.local_client import LocalLLM


@dataclass
class AnalysisResult:
    build_id: int
    report_markdown: str
    tool_calls: int


def _message_to_dict(msg: Any) -> dict[str, Any]:
    """OpenAI SDK message nesnesini sohbet gecmisine eklenebilir dict'e cevirir."""
    out: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
    if getattr(msg, "tool_calls", None):
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return out


class Orchestrator:
    def __init__(
        self,
        llm: LocalLLM | None = None,
        executor: ToolExecutor | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.llm = llm or LocalLLM(self.settings)
        self.executor = executor or ToolExecutor()

    def analyze(self, build_id: int, build_summary: str | None = None) -> AnalysisResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_task(build_id, build_summary)},
        ]

        tool_call_count = 0
        for _ in range(self.settings.llm_max_tool_iterations):
            msg = self.llm.chat(messages, tools=TOOL_SCHEMAS)
            messages.append(_message_to_dict(msg))

            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                return AnalysisResult(
                    build_id=build_id,
                    report_markdown=(msg.content or "").strip(),
                    tool_calls=tool_call_count,
                )

            for tc in tool_calls:
                tool_call_count += 1
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self.executor.call(tc.function.name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )

        # Iterasyon limiti doldu: son bir kez arasiz cevap iste.
        final = self.llm.chat(messages)
        return AnalysisResult(
            build_id=build_id,
            report_markdown=(final.content or "").strip(),
            tool_calls=tool_call_count,
        )
