"""Analiz sonucundan nihai markdown rapor uretimi."""

from __future__ import annotations

from datetime import datetime, timezone

from devops_agent.agent.orchestrator import AnalysisResult


def build_report(result: AnalysisResult, *, build_url: str | None = None) -> str:
    """Ajan ciktisini ust bilgi ekleyerek Build Summary'ye uygun markdown'a cevirir."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = f"# 🤖 DevOps AI — Build {result.build_id} Hata Analizi\n\n"
    meta = f"_Olusturulma: {ts}_"
    if build_url:
        meta += f" · [Build'i ac]({build_url})"
    body = result.report_markdown or "_Analiz uretilemedi._"
    return f"{header}{meta}\n\n---\n\n{body}\n"
