from __future__ import annotations

import random
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from freelance_hunter.connectors.base import BaseConnector
from freelance_hunter.domain.models.project import ClientProfile, MoneyRange, Project


class PlaywrightFreelancerConnector(BaseConnector):
    platform_name = "freelancer_playwright"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base_url = cfg.get("base_url", "https://www.freelancer.com")
        self.user_agent = cfg.get(
            "user_agent",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
        self.max_projects_per_run = cfg.get("max_projects_per_run", 20)
        self.session_dir = Path(cfg.get("session_dir", ".playwright/freelancer"))
        self.headless = cfg.get("headless", True)
        self.slow_mo_ms = cfg.get("slow_mo_ms", 0)
        self.goto_timeout_ms = cfg.get("goto_timeout_ms", 60000)

    def search_projects(self, keywords: list[str], limit: int = 20) -> list[Project]:
        limit = min(limit, self.max_projects_per_run)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        projects: list[Project] = []
        seen_urls: set[str] = set()
        search_paths = self.cfg.get("search_paths", [])

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=self.headless,
                slow_mo=self.slow_mo_ms,
                user_agent=self.user_agent,
                viewport={"width": 1366, "height": 900},
                locale="en-US",
                timezone_id="Asia/Singapore",
            )

            page = context.new_page()
            try:
                for path in search_paths:
                    if len(projects) >= limit:
                        break
                    url = urljoin(self.base_url, path)
                    try:
                        page.goto(url, timeout=self.goto_timeout_ms, wait_until="domcontentloaded")
                    except PlaywrightTimeoutError:
                        continue

                    self._human_delay(page)
                    html = page.content()
                    parsed = self._parse_search_page(html)

                    for project in parsed:
                        if project.url in seen_urls:
                            continue
                        seen_urls.add(project.url)
                        if self._matches_keywords(project, keywords):
                            projects.append(project)
                        if len(projects) >= limit:
                            break
            finally:
                context.close()

        return projects

    def fetch_project_detail(self, external_id: str) -> Project:
        raise NotImplementedError("Detail fetching is not yet implemented for PlaywrightFreelancerConnector")

    def submit_bid(self, external_id: str, bid: dict) -> dict:
        raise NotImplementedError("Bid submission is not enabled for PlaywrightFreelancerConnector")

    def sync_messages(self) -> list[dict]:
        return []

    def _human_delay(self, page) -> None:
        page.wait_for_timeout(random.randint(1800, 4200))

    def _parse_search_page(self, html: str) -> list[Project]:
        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.select('a[href*="/projects/"]')
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
            if not title or len(title) < 8:
                continue

            card_text = self._clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
            budget_min, budget_max, currency = self._extract_budget(card_text)
            skills = self._extract_skills(card_text)
            bids_count = self._extract_bids_count(card_text)
            external_id = self._extract_external_id(full_url)

            projects.append(
                Project(
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
                    bids_count=bids_count,
                    client=ClientProfile(),
                    raw_payload={"source": "playwright_search_page"},
                )
            )
        return projects

    def _matches_keywords(self, project: Project, keywords: list[str]) -> bool:
        if not keywords:
            return True
        haystack = f"{project.title} {project.description} {' '.join(project.skills)}".lower()
        return any(keyword.lower() in haystack for keyword in keywords)

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _extract_external_id(url: str) -> str:
        parts = [p for p in url.rstrip("/").split("/") if p]
        return "/" + "/".join(parts[-2:]) if len(parts) >= 2 else url

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
        match = re.search(r"(\d+)\s+bids?", text, flags=re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        known = [
            "React", "React.js", "Next.js", "JavaScript", "TypeScript", "Node.js", "Python",
            "Java", "Spring Boot", "PostgreSQL", "MySQL", "API", "Dashboard", "Admin",
            "Vue", "Angular", "Docker", "AWS"
        ]
        lowered = text.lower()
        return [item for item in known if item.lower() in lowered]
