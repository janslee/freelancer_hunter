from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from freelance_hunter.connectors.base import BaseConnector
from freelance_hunter.domain.models.project import ClientProfile, MoneyRange, Project


class FreelancerConnector(BaseConnector):
    platform_name = "freelancer"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base_url = cfg.get("base_url", "https://www.freelancer.com")
        self.timeout = cfg.get("request_timeout_seconds", 20)
        self.user_agent = cfg.get("user_agent", "Mozilla/5.0")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
        )

    def search_projects(self, keywords: list[str], limit: int = 20) -> list[Project]:
        search_paths = self.cfg.get("search_paths", [])
        max_projects = min(limit, self.cfg.get("max_projects_per_run", limit))
        projects: list[Project] = []
        seen_urls: set[str] = set()

        with self._client() as client:
            for path in search_paths:
                if len(projects) >= max_projects:
                    break
                url = urljoin(self.base_url, path)
                resp = client.get(url)
                resp.raise_for_status()
                parsed = self._parse_search_page(resp.text)
                for item in parsed:
                    if item.url in seen_urls:
                        continue
                    seen_urls.add(item.url)
                    projects.append(item)
                    if len(projects) >= max_projects:
                        break

        # Keyword filtering remains useful even when search_paths are predefined.
        if keywords:
            lowered = [k.lower() for k in keywords]
            filtered = []
            for project in projects:
                hay = f"{project.title} {project.description} {' '.join(project.skills)}".lower()
                if any(k in hay for k in lowered):
                    filtered.append(project)
            return filtered[:max_projects]

        return projects[:max_projects]

    def _parse_search_page(self, html: str) -> list[Project]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select('a[href*="/projects/"]')
        projects: list[Project] = []
        seen: set[str] = set()

        for anchor in cards:
            href = anchor.get("href")
            if not href:
                continue
            full_url = urljoin(self.base_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)

            title = self._clean_text(anchor.get_text(" ", strip=True))
            if not title or len(title) < 8:
                continue

            card_text = self._clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
            budget_min, budget_max, currency = self._extract_budget(card_text)
            skills = self._extract_skills(card_text)
            external_id = self._extract_external_id(full_url)

            project = Project(
                platform="freelancer",
                external_id=external_id,
                url=full_url,
                title=title,
                description=card_text,
                skills=skills,
                budget=MoneyRange(
                    currency=currency,
                    min_amount=budget_min,
                    max_amount=budget_max,
                    amount_type="fixed",
                ),
                bids_count=self._extract_bids_count(card_text),
                client=ClientProfile(),
                raw_payload={"source": "search_page"},
            )
            projects.append(project)

        return projects

    def fetch_project_detail(self, external_id: str) -> Project:
        raise NotImplementedError("Detail fetching is not yet implemented in the first connector version.")

    def submit_bid(self, external_id: str, bid: dict) -> dict:
        raise NotImplementedError("Bid submission is not yet implemented in the first connector version.")

    def sync_messages(self) -> list[dict]:
        return []

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _extract_external_id(url: str) -> str:
        parts = [p for p in url.rstrip("/").split("/") if p]
        return parts[-1] if parts else url

    @staticmethod
    def _extract_budget(text: str) -> tuple[float | None, float | None, str]:
        currency = "USD"
        if "£" in text:
            currency = "GBP"
        elif "€" in text:
            currency = "EUR"
        elif "$" in text:
            currency = "USD"

        amounts = re.findall(r"(?:USD|EUR|GBP|\$|€|£)\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", text)
        nums = [float(v.replace(',', '')) for v in amounts]
        if len(nums) >= 2:
            return nums[0], nums[1], currency
        if len(nums) == 1:
            return nums[0], nums[0], currency
        return None, None, currency

    @staticmethod
    def _extract_bids_count(text: str) -> int | None:
        m = re.search(r"(\d+)\s+bids?", text, flags=re.IGNORECASE)
        return int(m.group(1)) if m else None

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        known = [
            "React",
            "React.js",
            "Next.js",
            "JavaScript",
            "TypeScript",
            "Node.js",
            "Python",
            "Java",
            "Spring Boot",
            "PostgreSQL",
            "MySQL",
            "API",
            "Dashboard",
            "Admin",
        ]
        lowered = text.lower()
        skills = [item for item in known if item.lower() in lowered]
        return skills
