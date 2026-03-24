from __future__ import annotations

import json
import typer

from freelance_hunter.workflows.process_telegram_approvals import run as run_process_telegram_approvals
from freelance_hunter.workflows.submit_freelancer_bids_v2 import run as run_submit_freelancer_bids_v2
from freelance_hunter.workflows.notify_bid_submission_results import run as run_notify_bid_submission_results

app = typer.Typer(help="Extended CLI for approvals and Freelancer bid submission")


@app.command("process-telegram-approvals")
def process_telegram_approvals(db_path: str = "freelance_hunter.db"):
    count = run_process_telegram_approvals(db_path=db_path)
    typer.echo(f"Processed {count} Telegram approval commands")


@app.command("submit-freelancer-bids")
def submit_freelancer_bids(
    db_path: str = "freelance_hunter.db",
    limit: int = 1,
    headless: bool = False,
    dry_run: bool = True,
):
    result = run_submit_freelancer_bids_v2(db_path=db_path, limit=limit, headless=headless, dry_run=dry_run)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("notify-submission-results")
def notify_submission_results(db_path: str = "freelance_hunter.db"):
    count = run_notify_bid_submission_results(db_path=db_path)
    typer.echo(f"Notified {count} submission results")


if __name__ == "__main__":
    app()
