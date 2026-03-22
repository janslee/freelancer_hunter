from __future__ import annotations

from abc import ABC, abstractmethod

from freelance_hunter.domain.models.project import Project


class BaseConnector(ABC):
    platform_name: str

    @abstractmethod
    def search_projects(self, keywords: list[str], limit: int = 20) -> list[Project]:
        raise NotImplementedError

    @abstractmethod
    def fetch_project_detail(self, external_id: str) -> Project:
        raise NotImplementedError

    @abstractmethod
    def submit_bid(self, external_id: str, bid: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def sync_messages(self) -> list[dict]:
        raise NotImplementedError
