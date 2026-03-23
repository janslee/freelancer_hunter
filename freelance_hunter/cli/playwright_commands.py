from __future__ import annotations

import json
import typer

from freelance_hunter.workflows.scan_freelancer_projects_playwright import run as run_scan_playwright
from freelance_hunter.workflows.scan_freelancer_projects_detail import run as run_scan_detail
from freelance_hunter.workflows.debug_freelancer_detail import run as run_debug_detail
from freelance_hunter.workflows.notify_pending import run as run_notify_pending

app = typer.Typer(help="Supplemental Playwright CLI for Freelance Hunter")


@app.command("scan-freelancer-playwright")
def scan_freelancer_playwright(
    db_path: str = "freelance_hunter.db",
    limit: int = 10,
):
    count = run_scan_playwright(db_path=db_path, limit=limit)
    typer.echo(f"Scanned {count} Freelancer projects with Playwright list-page workflow")


@app.command("scan-freelancer-detail")
def scan_freelancer_detail(
    db_path: str = "freelance_hunter.db",
    limit: int = 5,
    headless: bool = False,
):
    count = run_scan_detail(db_path=db_path, limit=limit, headless=headless)
    typer.echo(f"Scanned {count} Freelancer projects with detail-page workflow")


@app.command("debug-freelancer-detail")
def debug_freelancer_detail(detail_url: str):
    result = run_debug_detail(detail_url)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("notify-pending")
def notify_pending(db_path: str = "freelance_hunter.db"):
    run_notify_pending(db_path=db_path)
    typer.echo("Sent pending approval notifications")


if __name__ == "__main__":
    app()
