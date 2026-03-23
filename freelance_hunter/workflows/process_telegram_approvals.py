from __future__ import annotations

from pathlib import Path
import re
import yaml
import httpx

from freelance_hunter.repositories.sqlite.db import get_connection, init_db


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
RUNTIME_DIR = BASE_DIR / ".runtime"
OFFSET_FILE = RUNTIME_DIR / "telegram_update_offset.txt"


class TelegramApprovalProcessor:
    def __init__(self, db_path: str = "freelance_hunter.db"):
        self.db_path = db_path
        self.notifications_cfg = self._load_yaml(CONFIG_DIR / "notifications.yaml")
        self.conn = get_connection(db_path)
        init_db(self.conn)
        self.telegram_cfg = self.notifications_cfg.get("notifications", {}).get("telegram", {})
        self.bot_token = self.telegram_cfg.get("bot_token", "")
        self.chat_id = str(self.telegram_cfg.get("chat_id", "")).strip()
        self.timeout_seconds = 20

    def process(self) -> int:
        if not self.telegram_cfg.get("enabled"):
            return 0
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram bot_token/chat_id is not configured")

        updates = self._fetch_updates()
        processed = 0
        max_update_id = self._read_offset()

        for item in updates:
            update_id = item.get("update_id", 0)
            max_update_id = max(max_update_id, update_id)
            message = item.get("message") or item.get("edited_message") or {}
            chat = message.get("chat", {})
            text = (message.get("text") or "").strip()
            if not text:
                continue
            if str(chat.get("id")) != self.chat_id:
                continue
            processed += self._process_command_text(text)

        self._write_offset(max_update_id)
        return processed

    def _process_command_text(self, text: str) -> int:
        normalized = re.sub(r"\s+", " ", text.strip())

        m = re.match(r"^approve\s+(\d+)\s*(\d+(?:\.\d+)?)?$", normalized, flags=re.IGNORECASE)
        if m:
            project_id = int(m.group(1))
            override_amount = float(m.group(2)) if m.group(2) else None
            self._approve_project(project_id, override_amount)
            self._send_text(f"Approved project {project_id}" + (f" with override amount {override_amount}" if override_amount else ""))
            return 1

        m = re.match(r"^skip\s+(\d+)$", normalized, flags=re.IGNORECASE)
        if m:
            project_id = int(m.group(1))
            self._skip_project(project_id)
            self._send_text(f"Skipped project {project_id}")
            return 1

        m = re.match(r"^aggressive\s+(\d+)$", normalized, flags=re.IGNORECASE)
        if m:
            project_id = int(m.group(1))
            self._apply_strategy(project_id, "aggressive_price", "aggressive")
            self._send_text(f"Applied aggressive pricing to project {project_id} and approved it")
            return 1

        m = re.match(r"^premium\s+(\d+)$", normalized, flags=re.IGNORECASE)
        if m:
            project_id = int(m.group(1))
            self._apply_strategy(project_id, "premium_price", "premium")
            self._send_text(f"Applied premium pricing to project {project_id} and approved it")
            return 1

        return 0

    def _approve_project(self, project_id: int, override_amount: float | None) -> None:
        project = self.conn.execute("SELECT id, status FROM projects WHERE id = ?", (project_id,)).fetchone()
        if project is None:
            raise ValueError(f"Project {project_id} does not exist")

        if override_amount is not None:
            self.conn.execute(
                """
                UPDATE bid_drafts
                SET proposed_amount = ?, status = 'approved'
                WHERE project_id = ?
                AND id = (SELECT id FROM bid_drafts WHERE project_id = ? ORDER BY id DESC LIMIT 1)
                """,
                (override_amount, project_id, project_id),
            )
        else:
            self.conn.execute(
                """
                UPDATE bid_drafts
                SET status = 'approved'
                WHERE project_id = ?
                AND id = (SELECT id FROM bid_drafts WHERE project_id = ? ORDER BY id DESC LIMIT 1)
                """,
                (project_id, project_id),
            )

        self.conn.execute("UPDATE projects SET status = 'APPROVED' WHERE id = ?", (project_id,))
        self.conn.commit()

    def _skip_project(self, project_id: int) -> None:
        self.conn.execute("UPDATE projects SET status = 'SKIPPED' WHERE id = ?", (project_id,))
        self.conn.execute(
            "UPDATE bid_drafts SET status = 'skipped' WHERE project_id = ? AND status IN ('draft', 'notified')",
            (project_id,),
        )
        self.conn.commit()

    def _apply_strategy(self, project_id: int, field_name: str, strategy_name: str) -> None:
        pricing = self.conn.execute(
            f"SELECT {field_name} AS amount FROM pricing_decisions WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if pricing is None or pricing["amount"] is None:
            raise ValueError(f"Pricing decision for project {project_id} not found")

        self.conn.execute(
            """
            UPDATE bid_drafts
            SET proposed_amount = ?, style = ?, status = 'approved'
            WHERE project_id = ?
            AND id = (SELECT id FROM bid_drafts WHERE project_id = ? ORDER BY id DESC LIMIT 1)
            """,
            (pricing["amount"], strategy_name, project_id, project_id),
        )
        self.conn.execute("UPDATE projects SET status = 'APPROVED' WHERE id = ?", (project_id,))
        self.conn.commit()

    def _fetch_updates(self) -> list[dict]:
        offset = self._read_offset() + 1
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "timeout": 10,
            "offset": offset,
            "allowed_updates": ["message", "edited_message"],
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram getUpdates failed: {data}")
        return data.get("result", [])

    def _send_text(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

    def _read_offset(self) -> int:
        if not OFFSET_FILE.exists():
            return 0
        try:
            return int(OFFSET_FILE.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            return 0

    def _write_offset(self, value: int) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        OFFSET_FILE.write_text(str(value), encoding="utf-8")

    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


def run(db_path: str = "freelance_hunter.db") -> int:
    processor = TelegramApprovalProcessor(db_path=db_path)
    return processor.process()
