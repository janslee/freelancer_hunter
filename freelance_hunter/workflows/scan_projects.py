from __future__ import annotations

from freelance_hunter.app.bootstrap import bootstrap_app



def run(db_path: str = "freelance_hunter.db") -> None:
    app = bootstrap_app(db_path=db_path)
    # Placeholder for real platform connectors.
    # For now this workflow does not fetch external projects.
    _ = app
