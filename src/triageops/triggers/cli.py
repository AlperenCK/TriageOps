"""CLI tetikleyici — pipeline YAML adimindan (condition: failed()) cagrilir.

Kullanim:
  triageops analyze --build-id 12345
  triageops analyze --build-id 12345 --in-pipeline   # Build Summary'ye yazar
"""

from __future__ import annotations

from pathlib import Path

import typer

from triageops.agent.orchestrator import Orchestrator
from triageops.ado.builds import BuildReader
from triageops.ado.client import AdoClient
from triageops.ado.writeback import emit_build_summary_logging_command, emit_log_issue
from triageops.config import get_settings
from triageops.report import build_report

app = typer.Typer(add_completion=False, help="Azure DevOps TriageOps ajani")


@app.command()
def analyze(
    build_id: int = typer.Option(..., "--build-id", "-b", help="Analiz edilecek build id"),
    in_pipeline: bool = typer.Option(
        False, "--in-pipeline", help="Sonucu Build Summary'ye logging komutuyla yazar"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Raporu bu dosyaya yaz"),
) -> None:
    """Bir build'in hatasini analiz eder ve markdown rapor uretir."""
    settings = get_settings()

    summary = None
    try:
        b = BuildReader(AdoClient(settings)).get_build(build_id)
        summary = (
            f"definition={b.get('definition', {}).get('name')} "
            f"branch={b.get('sourceBranch')} result={b.get('result')}"
        )
        build_url = (b.get("_links", {}).get("web", {}) or {}).get("href")
    except Exception as exc:  # noqa: BLE001 - build ozeti opsiyonel
        typer.echo(f"[uyari] Build ozeti alinamadi: {exc}", err=True)
        build_url = None

    result = Orchestrator(settings=settings).analyze(build_id, build_summary=summary)
    report = build_report(result, build_url=build_url)

    if output:
        output.write_text(report, encoding="utf-8")
        typer.echo(f"Rapor yazildi: {output}")

    if in_pipeline:
        emit_build_summary_logging_command(report)
        emit_log_issue(
            f"TriageOps analizi tamamlandi ({result.tool_calls} arac cagrisi). "
            "Ayrintilar Build Summary sekmesinde."
        )
    else:
        typer.echo(report)


if __name__ == "__main__":
    app()
