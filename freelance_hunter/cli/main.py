import typer

from freelance_hunter.workflows.scan_projects import run as run_scan
from freelance_hunter.workflows.evaluate_projects import run as run_evaluate
from freelance_hunter.workflows.draft_bids import run as run_draft
from freelance_hunter.repositories.sqlite.db import get_connection, init_db
from freelance_hunter.workflows.seed_mock_projects import run as run_seed

app = typer.Typer(help="Freelance Hunter CLI")


@app.command("init-db")
def init_db_command(db_path: str = "freelance_hunter.db"):
    conn = get_connection(db_path)
    init_db(conn)
    typer.echo(f"Initialized database: {db_path}")


@app.command("seed-mock-projects")
def seed_mock_projects(db_path: str = "freelance_hunter.db"):
    run_seed(db_path=db_path)
    typer.echo("Seeded mock projects")


@app.command("scan-projects")
def scan_projects(db_path: str = "freelance_hunter.db"):
    run_scan(db_path=db_path)
    typer.echo("Scanned projects")


@app.command("evaluate-projects")
def evaluate_projects(db_path: str = "freelance_hunter.db"):
    run_evaluate(db_path=db_path)
    typer.echo("Evaluated projects")


@app.command("draft-bids")
def draft_bids(db_path: str = "freelance_hunter.db"):
    run_draft(db_path=db_path)
    typer.echo("Drafted bids")


if __name__ == "__main__":
    app()
