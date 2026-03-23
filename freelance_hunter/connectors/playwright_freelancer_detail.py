from __future__ import annotations

import json
import random
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from freelance_hunter.connectors.base import BaseConnector
from freelance_hunter.domain.models.project import ClientProfile, MoneyRange, Project


class PlaywrightFreelancerDetailConnector(BaseConnector):
    platform_name = "freelancer_playwright_detail"

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
        self.debug_dir = Path(cfg.get("debug_dir", ".debug/freelancer"))

    def search_projects(self, keywords: list[str], limit: int = 20) -> list[Project]:
        limit = min(limit, self.max_projects_per_run)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
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
                    search_items = self._parse_search_page(html)

                    for item in search_items:
                        if item.url in seen_urls:
                            continue
                        seen_urls.add(item.url)
                        try:
                            detail_project = self._fetch_project_detail_by_url(context, item.url)
                        except Exception:
                            detail_project = item
                        if self._matches_keywords(detail_project, keywords):
                            projects.append(detail_project)
                        if len(projects) >= limit:
                            break
            finally:
                context.close()
        return projects

    def fetch_project_detail(self, external_id: str) -> Project:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        detail_url = urljoin(self.base_url, external_id)
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
            try:
                return self._fetch_project_detail_by_url(context, detail_url)
            finally:
                context.close()

    def submit_bid(self, external_id: str, bid: dict) -> dict:
        raise NotImplementedError("Bid submission is not enabled for PlaywrightFreelancerDetailConnector")

    def sync_messages(self) -> list[dict]:
        return []

    def _fetch_project_detail_by_url(self, context, detail_url: str) -> Project:
        page = context.new_page()
        try:
            page.goto(detail_url, timeout=self.goto_timeout_ms, wait_until="domcontentloaded")
            self._human_delay(page)
            html = page.content()
            return self._parse_detail_page(detail_url, html)
        except Exception:
            self._save_debug(page, detail_url)
            raise
        finally:
            page.close()

    def _save_debug(self, page, detail_url: str) -> None:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", detail_url)[-120:]
        try:
            page.screenshot(path=str(self.debug_dir / f"{safe_name}.png"), full_page=True)
        except Exception:
            pass
        try:
            html = page.content()
            (self.debug_dir / f"{safe_name}.html").write_text(html, encoding="utf-8")
        except Exception:
            pass

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
                    budget=MoneyRange(currency=currency, min_amount=budget_min, max_amount=budget_max, amount_type="fixed"),
                    bids_count=bids_count,
                    client=ClientProfile(),
                    raw_payload={"source": "playwright_search_page"},
                )
            )
        return projects

    def _parse_detail_page(self, detail_url: str, html: str) -> Project:
        soup = BeautifulSoup(html, "html.parser")
        text = self._clean_text(soup.get_text(" ", strip=True))
        title = self._extract_title(soup, text, detail_url)
        description = self._extract_description(soup, html, text)
        budget_min, budget_max, currency = self._extract_budget(text)
        skills = self._extract_skills_from_detail(soup, text)
        bids_count = self._extract_bids_count(text)
        client = self._extract_client_profile(soup, text)
        external_id = self._extract_external_id(detail_url)

        raw_payload = {
            "source": "playwright_detail_page",
            "has_description": bool(description),
            "skills_count": len(skills),
        }

        return Project(
            platform="freelancer",
            external_id=external_id,
            url=detail_url,
            title=title,
            description=description,
            skills=skills,
            budget=MoneyRange(currency=currency, min_amount=budget_min, max_amount=budget_max, amount_type="fixed"),
            bids_count=bids_count,
            client=client,
            raw_payload=raw_payload,
        )

    def _extract_title(self, soup: BeautifulSoup, text: str, detail_url: str) -> str:
        og = soup.select_one('meta[property="og:title"]')
        if og and og.get("content"):
            return self._normalize_title(og.get("content"))
        if soup.title and soup.title.string:
            return self._normalize_title(soup.title.string)
        h1 = soup.find("h1")
        if h1:
            return self._normalize_title(h1.get_text(" ", strip=True))
        return detail_url.rstrip('/').split('/')[-1].replace('-', ' ').title()

    def _extract_description(self, soup: BeautifulSoup, html: str, text: str) -> str:
        og = soup.select_one('meta[property="og:description"]')
        if og and og.get("content"):
            return self._clean_text(og.get("content"))[:4000]
        meta = soup.select_one('meta[name="description"]')
        if meta and meta.get("content"):
            return self._clean_text(meta.get("content"))[:4000]
        for selector in [
            '[data-testid="project-description"]',
            '.ProjectDescription',
            '.PageProjectViewLogout-detail-paragraph',
            '.project-description',
        ]:
            node = soup.select_one(selector)
            if node:
                return self._clean_text(node.get_text(" ", strip=True))[:4000]
        json_match = re.search(r'"description"\s*:\s*"(.*?)"', html, flags=re.IGNORECASE | re.DOTALL)
        if json_match:
            raw = json_match.group(1)
            raw = raw.encode('utf-8').decode('unicode_escape', errors='ignore')
            return self._clean_text(raw)[:4000]
        return text[:1500]

    def _extract_skills_from_detail(self, soup: BeautifulSoup, text: str) -> list[str]:
        skills: list[str] = []
        for selector in ['a[href*="/jobs/"], a[href*="/skills/"]', '.skillsList a', '[data-testid="skills"] a']:
            for node in soup.select(selector):
                label = self._clean_text(node.get_text(" ", strip=True))
                if 1 < len(label) < 40 and label not in skills:
                    skills.append(label)
        if skills:
            return skills[:20]
        return self._extract_skills(text)

    def _extract_client_profile(self, soup: BeautifulSoup, text: str) -> ClientProfile:
        rating = None
        rating_match = re.search(r'([0-5](?:\.\d)?)\s*/\s*5', text)
        if rating_match:
            try:
                rating = float(rating_match.group(1))
            except ValueError:
                rating = None

        payment_verified = bool(re.search(r'payment\s+verified', text, flags=re.IGNORECASE))
        country = None
        country_match = re.search(r'(?:from|location)\s+([A-Z][A-Za-z\s]{2,40})', text, flags=re.IGNORECASE)
        if country_match:
            country = self._clean_text(country_match.group(1))

        name = None
        for selector in ['[data-testid="client-name"]', '.FreelancerInfo-name', '.username']:
            node = soup.select_one(selector)
            if node:
                name = self._clean_text(node.get_text(" ", strip=True))
                break

        return ClientProfile(name=name, country=country, rating=rating, payment_verified=payment_verified)

    def _matches_keywords(self, project: Project, keywords: list[str]) -> bool:
        if not keywords:
            return True
        haystack = f"{project.title} {project.description} {' '.join(project.skills)}".lower()
        return any(keyword.lower() in haystack for keyword in keywords)

    def _normalize_title(self, value: str) -> str:
        value = self._clean_text(value)
        value = re.sub(r'\s*\|\s*Freelancer.*$', '', value, flags=re.IGNORECASE)
        return value

    @staticmethod
    def _clean_text(value: str) -> str:
        value = value.replace('\\n', ' ').replace('\\t', ' ')
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    @staticmethod
    def _extract_external_id(url: str) -> str:
        parts = [p for p in url.rstrip('/').split('/') if p]
        return '/' + '/'.join(parts[-2:]) if len(parts) >= 2 else url

    @staticmethod
    def _extract_budget(text: str) -> tuple[float | None, float | None, str]:
        currency = 'USD'
        if '£' in text:
            currency = 'GBP'
        elif '€' in text:
            currency = 'EUR'
        elif '$' in text:
            currency = 'USD'

        amounts = re.findall(r'(?:USD|EUR|GBP|\$|€|£)\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', text)
        nums = [float(v.replace(',', '')) for v in amounts]
        if len(nums) >= 2:
            return nums[0], nums[1], currency
        if len(nums) == 1:
            return nums[0], nums[0], currency
        return None, None, currency

    @staticmethod
    def _extract_bids_count(text: str) -> int | None:
        match = re.search(r'(\d+)\s+bids?', text, flags=re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        known = [
            'React', 'React.js', 'Next.js', 'JavaScript', 'TypeScript', 'Node.js', 'Python',
            'Java', 'Spring Boot', 'PostgreSQL', 'MySQL', 'API', 'Dashboard', 'Admin',
            'Vue', 'Angular', 'Docker', 'AWS', 'MongoDB', 'Laravel', 'Django'
        ]
        lowered = text.lower()
        return [item for item in known if item.lower() in lowered]
