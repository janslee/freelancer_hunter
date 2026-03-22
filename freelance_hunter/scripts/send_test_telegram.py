from __future__ import annotations

import os
from pathlib import Path

import yaml

from freelance_hunter.integrations.notifier.telegram import TelegramNotifier


def load_notification_cfg() -> dict:
    config_path = Path(__file__).resolve().parents[2] / "config" / "notifications.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("notifications", {}).get("telegram", {})


def main() -> None:
    cfg = load_notification_cfg()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or cfg.get("bot_token", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or cfg.get("chat_id", "")

    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    notifier.send_text("freelancer_hunter Telegram test message")
    print("Telegram message sent")


if __name__ == "__main__":
    main()
