from __future__ import annotations

from pathlib import Path
import yaml

from freelance_hunter.integrations.notifier.telegram import TelegramNotifier
from freelance_hunter.repositories.sqlite.db import get_connection, init_db


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run(db_path: str = "freelance_hunter.db") -> int:
    notifications_cfg = _load_yaml(CONFIG_DIR / "notifications.yaml")
    telegram_cfg = notifications_cfg.get("notifications", {}).get("telegram", {})
    if not telegram_cfg.get("enabled"):
        return 0

    conn = get_connection(db_path)
    init_db(conn)

    notifier = TelegramNotifier(
        bot_token=telegram_cfg.get("bot_token", ""),
        chat_id=str(telegram_cfg.get("chat_id", "")),
    )

    projects = conn.execute(
        "SELECT id, platform, title, url FROM projects WHERE status = 'APPROVAL_PENDING' ORDER BY id ASC"
    ).fetchall()

    sent = 0
    for project in projects:
        pricing = conn.execute(
            "SELECT * FROM pricing_decisions WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project["id"],),
        ).fetchone()
        evaluation = conn.execute(
            "SELECT * FROM evaluations WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project["id"],),
        ).fetchone()
        if pricing is None or evaluation is None:
            continue

        notifier.send_approval_request(
            {
                "project_id": project["id"],
                "platform": project["platform"],
                "title": project["title"],
                "overall_score": evaluation["overall_score"],
                "risk_score": evaluation["risk_score"],
                "currency": pricing["currency"],
                "suggested_price": pricing["suggested_price"],
                "url": project["url"],
            }
        )
        sent += 1
    return sent
