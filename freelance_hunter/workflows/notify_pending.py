from __future__ import annotations

from freelance_hunter.app.bootstrap import bootstrap_app
from freelance_hunter.integrations.notifier.telegram import TelegramNotifier



def run(db_path: str = "freelance_hunter.db") -> None:
    app = bootstrap_app(db_path=db_path)
    telegram_cfg = app.settings.get("notifications", {}).get("telegram", {})
    if not telegram_cfg.get("enabled"):
        return

    notifier = TelegramNotifier(
        bot_token=telegram_cfg.get("bot_token", ""),
        chat_id=telegram_cfg.get("chat_id", ""),
    )

    projects = app.project_repo.list_by_status("APPROVAL_PENDING")
    for project_id, project in projects:
        pricing = app.pricing_repo.get_latest(project_id)
        evaluations = app.conn.execute(
            "SELECT * FROM evaluations WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if evaluations is None:
            continue
        notifier.send_approval_request(
            {
                "project_id": project_id,
                "platform": project.platform,
                "title": project.title,
                "overall_score": evaluations["overall_score"],
                "risk_score": evaluations["risk_score"],
                "currency": pricing["currency"],
                "suggested_price": pricing["suggested_price"],
                "url": project.url,
            }
        )
