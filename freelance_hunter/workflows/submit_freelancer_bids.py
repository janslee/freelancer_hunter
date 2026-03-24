from __future__ import annotations

from pathlib import Path
import json
import re
import yaml

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from freelance_hunter.repositories.sqlite.db import get_connection, init_db


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
DEBUG_DIR = BASE_DIR / ".debug" / "freelancer_submit"
SESSION_DIR = BASE_DIR / ".playwright" / "freelancer"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class FreelancerBidSubmitter:
    def __init__(self, db_path: str = "freelance_hunter.db"):
        self.db_path = db_path
        self.platforms_cfg = _load_yaml(CONFIG_DIR / "platforms.yaml")
        self.accounts_cfg = _load_yaml(CONFIG_DIR / "accounts.yaml")
        self.freelancer_cfg = self.platforms_cfg.get("platforms", {}).get("freelancer", {})
        self.account_cfg = self.accounts_cfg.get("accounts", {}).get("freelancer", {})
        self.base_url = self.freelancer_cfg.get("base_url", "https://www.freelancer.com")
        self.user_agent = self.freelancer_cfg.get(
            "user_agent",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
        self.goto_timeout_ms = self.freelancer_cfg.get("goto_timeout_ms", 60000)
        self.conn = get_connection(db_path)
        init_db(self.conn)
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    def run(self, limit: int = 3, headless: bool = False) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT p.id, p.url, p.title, b.id AS bid_id, b.proposed_amount, b.currency, b.body
            FROM projects p
            JOIN bid_drafts b ON b.project_id = p.id
            WHERE p.status = 'APPROVED'
              AND b.status = 'approved'
            ORDER BY p.id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        results: list[dict] = []
        if not rows:
            return results

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=headless,
                user_agent=self.user_agent,
                viewport={"width": 1366, "height": 900},
                locale="en-US",
                timezone_id="Asia/Singapore",
            )
            try:
                page = context.new_page()
                self._ensure_login(page)
                for row in rows:
                    result = self._submit_one(page, row)
                    results.append(result)
                    self._update_db_after_attempt(row["id"], row["bid_id"], result)
            finally:
                context.close()
        return results

    def _ensure_login(self, page) -> None:
        if not self.account_cfg.get("enabled"):
            return
        login_url = self.account_cfg.get("login_url", f"{self.base_url}/login")
        email = self.account_cfg.get("email", "")
        password = self.account_cfg.get("password", "")
        if not email or not password:
            return

        try:
            page.goto(login_url, timeout=self.goto_timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
        except PlaywrightTimeoutError:
            return

        current = page.content().lower()
        if "logout" in current or "dashboard" in current:
            return

        selectors_email = [
            'input[type="email"]',
            'input[name="username"]',
            'input[name="login"]',
        ]
        selectors_password = [
            'input[type="password"]',
            'input[name="password"]',
        ]
        submit_selectors = [
            'button[type="submit"]',
            'button[data-testid="login-submit"]',
        ]

        for sel in selectors_email:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(email)
                break
        for sel in selectors_password:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(password)
                break
        for sel in submit_selectors:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.click()
                page.wait_for_timeout(5000)
                break

    def _submit_one(self, page, row) -> dict:
        project_id = row["id"]
        detail_url = row["url"]
        bid_amount = row["proposed_amount"]
        proposal_text = row["body"]

        try:
            page.goto(detail_url, timeout=self.goto_timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
        except Exception as exc:
            self._save_debug(page, project_id, "goto_failed")
            return {"success": False, "project_id": project_id, "reason": f"goto_failed: {exc}"}

        bid_button_selectors = [
            'button:has-text("Bid on this Project")',
            'button:has-text("Place Bid")',
            'a:has-text("Bid on this Project")',
            'a:has-text("Place Bid")',
        ]

        opened_bid_form = False
        for sel in bid_button_selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                try:
                    locator.first.click()
                    page.wait_for_timeout(2500)
                    opened_bid_form = True
                    break
                except Exception:
                    pass

        if not opened_bid_form:
            self._save_debug(page, project_id, "bid_form_not_found")
            return {"success": False, "project_id": project_id, "reason": "bid_form_not_found"}

        amount_selectors = [
            'input[name="bid"]',
            'input[name="amount"]',
            'input[inputmode="decimal"]',
            'input[type="number"]',
        ]
        text_selectors = [
            'textarea',
            'textarea[name="proposal"]',
            '[contenteditable="true"]',
        ]
        submit_selectors = [
            'button:has-text("Submit Bid")',
            'button:has-text("Place Bid")',
            'button[type="submit"]',
        ]

        amount_filled = False
        for sel in amount_selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                try:
                    locator.first.fill(str(bid_amount))
                    amount_filled = True
                    break
                except Exception:
                    pass

        text_filled = False
        for sel in text_selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                try:
                    if "contenteditable" in sel:
                        locator.first.click()
                        locator.first.fill(proposal_text)
                    else:
                        locator.first.fill(proposal_text)
                    text_filled = True
                    break
                except Exception:
                    pass

        if not amount_filled or not text_filled:
            self._save_debug(page, project_id, "form_fill_failed")
            return {
                "success": False,
                "project_id": project_id,
                "reason": f"form_fill_failed amount={amount_filled} text={text_filled}",
            }

        # 默认先做安全模式：点击前截图，实际提交需要你确认后再放开。
        self._save_debug(page, project_id, "ready_to_submit")

        # 可以在稳定后改成真正 click submit。
        submit_found = False
        for sel in submit_selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                submit_found = True
                break

        if not submit_found:
            return {"success": False, "project_id": project_id, "reason": "submit_button_not_found"}

        return {
            "success": False,
            "project_id": project_id,
            "reason": "ready_to_submit_manual_gate",
            "detail_url": detail_url,
        }

    def _update_db_after_attempt(self, project_id: int, bid_id: int, result: dict) -> None:
        if result.get("success"):
            self.conn.execute("UPDATE projects SET status = 'BID_SUBMITTED' WHERE id = ?", (project_id,))
            self.conn.execute("UPDATE bid_drafts SET status = 'submitted' WHERE id = ?", (bid_id,))
        else:
            self.conn.execute("UPDATE projects SET status = 'NEEDS_HUMAN' WHERE id = ?", (project_id,))
            self.conn.execute("UPDATE bid_drafts SET status = 'ready_to_submit' WHERE id = ?", (bid_id,))
        self.conn.commit()

    def _save_debug(self, page, project_id: int, stage: str) -> None:
        safe = f"project_{project_id}_{stage}"
        try:
            page.screenshot(path=str(DEBUG_DIR / f"{safe}.png"), full_page=True)
        except Exception:
            pass
        try:
            html = page.content()
            (DEBUG_DIR / f"{safe}.html").write_text(html, encoding="utf-8")
        except Exception:
            pass


def run(db_path: str = "freelance_hunter.db", limit: int = 3, headless: bool = False) -> list[dict]:
    submitter = FreelancerBidSubmitter(db_path=db_path)
    return submitter.run(limit=limit, headless=headless)
