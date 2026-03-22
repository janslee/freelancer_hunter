from __future__ import annotations

from abc import ABC, abstractmethod


class Notifier(ABC):
    @abstractmethod
    def send_text(self, message: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_approval_request(self, payload: dict) -> None:
        raise NotImplementedError
