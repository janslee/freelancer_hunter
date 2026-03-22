from __future__ import annotations

from freelance_hunter.app.bootstrap import bootstrap_app



def run(db_path: str = "freelance_hunter.db") -> None:
    app = bootstrap_app(db_path=db_path)
    projects = app.project_repo.list_by_status("DISCOVERED")

    for project_id, project in projects:
        evaluation = app.scorer.evaluate(project)
        pricing = app.pricing_engine.calculate(project)

        app.evaluation_repo.save(project_id, evaluation)
        app.pricing_repo.save(project_id, pricing)
        app.project_repo.update_status(project_id, "EVALUATED")
