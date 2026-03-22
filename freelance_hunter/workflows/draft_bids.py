from __future__ import annotations

from freelance_hunter.app.bootstrap import bootstrap_app



def run(db_path: str = "freelance_hunter.db") -> None:
    app = bootstrap_app(db_path=db_path)
    projects = app.project_repo.list_by_status("EVALUATED")

    for project_id, project in projects:
        pricing = app.pricing_repo.get_latest(project_id)
        bid = app.proposal_generator.generate_standard(project, pricing)
        app.bid_repo.save(project_id, bid)
        app.project_repo.update_status(project_id, "APPROVAL_PENDING")
