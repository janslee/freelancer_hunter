from __future__ import annotations

import httpx

from freelance_hunter.integrations.notifier.base import Notifier


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str, timeout_seconds: int = 20):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout_seconds = timeout_seconds

    def send_text(self, message: str) -> None:
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram bot_token/chat_id is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

    def send_approval_request(self, payload: dict) -> None:
        message = self._build_approval_message(payload)
        self.send_text(message)

    def _build_approval_message(self, payload: dict) -> str:
        return (
            "[待报价审批]\n"
            f"项目ID: {payload.get('project_id')}\n"
            f"平台: {payload.get('platform')}\n"
            f"标题: {payload.get('title')}\n"
            f"评分: {payload.get('overall_score')}\n"
            f"风险: {payload.get('risk_score')}\n"
            f"建议报价: {payload.get('currency')} {payload.get('suggested_price')}\n"
            f"链接: {payload.get('url')}\n\n"
            "可回复命令:\n"
            f"approve {payload.get('project_id')}\n"
            f"approve {payload.get('project_id')} 720\n"
            f"skip {payload.get('project_id')}"
        )
