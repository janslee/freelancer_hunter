from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from freelance_hunter.connectors.base import BaseConnector
from freelance_hunter.domain.models.project import ClientProfile, MoneyRange, Project


class ZBJConnector(BaseConnector):
    platform_name = "zbj"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base_url = cfg.get("base_url", "https://task.zbj.com")
        self.timeout = cfg.get("request_timeout_seconds", 20)
        self.user_agent = cfg.get("user_agent", "Mozilla/5.0")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
        )

    def search_projects(self, keywords: list[str], limit: int = 20) -> list[Project]:
        # 初版使用关键词搜索页面，后续再针对真实页面结构加强。
        projects: list[Project] = []
        seen_urls: set[str] = set()
        with self._client() as client:
            for keyword in keywords[:5]:
                url = f"{self.base_url}/search/service/?kw={keyword}"
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                except Exception:
                    continue
                for item in self._parse_search_page(resp.text):
                    if item.url in seen_urls:
                        continue
                    seen_urls.add(item.url)
                    projects.append(item)
                    if len(projects) >= limit:
                        return projects
        return projects

    def _parse_search_page(self, html: str) -> list[Project]:
        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.select('a[href*="/task/"]')
        projects: list[Project] = []
        seen: set[str] = set()
        for anchor in anchors:
            href = anchor.get("href")
            if not href:
                continue
            full_url = urljoin(self.base_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)

            title = self._clean_text(anchor.get_text(" ", strip=True))
            if not title or len(title) < 4:
                continue
            card_text = self._clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
            budget_min, budget_max = self._extract_budget(card_text)
            external_id = self._extract_external_id(full_url)
            skills = self._extract_skills(card_text)

            projects.append(
                Project(
                    platform="zbj",
                    external_id=external_id,
                    url=full_url,
                    title=title,
                    description=card_text,
                    skills=skills,
                    budget=MoneyRange(currency="CNY", min_amount=budget_min, max_amount=budget_max, amount_type="fixed"),
                    bids_count=None,
                    client=ClientProfile(),
                    raw_payload={"source": "zbj_search_page"},
                )
            )
        return projects

    def fetch_project_detail(self, external_id: str) -> Project:
        raise NotImplementedError("ZBJ detail fetching is not yet implemented")

    def submit_bid(self, external_id: str, bid: dict) -> dict:
        raise NotImplementedError("ZBJ bid submission is not yet implemented")

    def sync_messages(self) -> list[dict]:
        return []

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _extract_external_id(url: str) -> str:
        parts = [p for p in url.rstrip('/').split('/') if p]
        return '/'.join(parts[-2:]) if len(parts) >= 2 else url

    @staticmethod
    def _extract_budget(text: str) -> tuple[float | None, float | None]:
        amounts = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*元", text)
        nums = [float(v) for v in amounts]
        if len(nums) >= 2:
            return nums[0], nums[1]
        if len(nums) == 1:
            return nums[0], nums[0]
        return None, None

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        known = [
            "React", "Next.js", "JavaScript", "Node.js", "Python", "Java", "Spring Boot",
            "PostgreSQL", "MySQL", "小程序", "网站", "后台", "管理系统", "商城", "接口",
        ]
        lowered = text.lower()
        return [item for item in known if item.lower() in lowered]
