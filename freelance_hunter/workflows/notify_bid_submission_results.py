from __future__ import annotations

from pathlib import Path
import yaml

from freelance_hunter.integrations.notifier.telegram import TelegramNotifier
from freelance_hunter.repositories.sqlite.db import get_connection, init_db


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
RUNTIME_DIR = BASE_DIR / ".runtime"
NOTIFIED_FILE = RUNTIME_DIR / "submission_notifications_sent.txt"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _read_sent_ids() -> set[int]:
    if not NOTIFIED_FILE.exists():
        return set()
    ids: set[int] = set()
    for line in NOTIFIED_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.isdigit():
            ids.add(int(line))
    return ids


def _append_sent_id(project_id: int) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with NOTIFIED_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{project_id}\n")


def run(db_path: str = "freelance_hunter.db") -> int:
    notifications_cfg = _load_yaml(CONFIG_DIR / "notifications.yaml")
    telegram_cfg = notifications_cfg.get("notifications", {}).get("telegram", {})
    if not telegram_cfg.get("enabled"):
        return 0

    conn = get_connection(db_path)
    init_db(conn)

    rows = conn.execute(
        """
        SELECT p.id, p.title, p.url, p.status, b.status AS bid_status, b.proposed_amount, b.currency
        FROM projects p
        LEFT JOIN bid_drafts b ON b.project_id = p.id
        WHERE p.status IN ('BID_SUBMITTED', 'NEEDS_HUMAN')
        ORDER BY p.id ASC, b.id DESC
        """
    ).fetchall()

    sent_ids = _read_sent_ids()
    notifier = TelegramNotifier(
        bot_token=telegram_cfg.get("bot_token", ""),
        chat_id=telegram_cfg.get("chat_id", ""),
    )

    processed = 0
    seen_project_ids: set[int] = set()
    for row in rows:
        project_id = int(row["id"])
        if project_id in sent_ids or project_id in seen_project_ids:
            continue
        seen_project_ids.add(project_id)

        if row["status"] == "BID_SUBMITTED":
            msg = (
                "[报价提交结果]\n"
                f"项目ID: {project_id}\n"
                f"标题: {row['title']}\n"
                f"状态: 已提交\n"
                f"金额: {row['currency']} {row['proposed_amount']}\n"
                f"链接: {row['url']}"
            )
        else:
            msg = (
                "[报价提交结果]\n"
                f"项目ID: {project_id}\n"
                f"标题: {row['title']}\n"
                f"状态: 需要人工处理\n"
                f"草稿状态: {row['bid_status']}\n"
                f"金额: {row['currency']} {row['proposed_amount']}\n"
                f"链接: {row['url']}"
            )
        notifier.send_text(msg)
        _append_sent_id(project_id)
        processed += 1

    return processed
