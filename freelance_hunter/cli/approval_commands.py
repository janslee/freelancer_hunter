from __future__ import annotations

import typer

from freelance_hunter.workflows.process_telegram_approvals import run as run_process_telegram_approvals

app = typer.Typer(help="Approval processing CLI for Freelance Hunter")


@app.command("process-telegram-approvals")
def process_telegram_approvals(db_path: str = "freelance_hunter.db"):
    count = run_process_telegram_approvals(db_path=db_path)
    typer.echo(f"Processed {count} Telegram approval commands")


if __name__ == "__main__":
    app()
