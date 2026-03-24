from __future__ import annotations

from pathlib import Path
import json
import yaml

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from freelance_hunter.repositories.sqlite.db import get_connection, init_db


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
DEBUG_DIR = BASE_DIR / ".debug" / "freelancer_submit_v2"
SESSION_DIR = BASE_DIR / ".playwright" / "freelancer"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class FreelancerBidSubmitterV2:
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

    def run(self, limit: int = 3, headless: bool = False, dry_run: bool = True) -> list[dict]:
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
                    result = self._submit_one(page, row, dry_run=dry_run)
                    results.append(result)
                    self._update_db_after_attempt(row["id"], row["bid_id"], result, dry_run=dry_run)
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
        if "logout" in current or "dashboard" in current or "notifications" in current:
            return

        for sel in ['input[type="email"]', 'input[name="username"]', 'input[name="login"]']:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(email)
                break
        for sel in ['input[type="password"]', 'input[name="password"]']:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(password)
                break
        for sel in ['button[type="submit"]', 'button[data-testid="login-submit"]']:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.click()
                page.wait_for_timeout(5000)
                break

    def _submit_one(self, page, row, dry_run: bool) -> dict:
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

        if self._page_looks_like_challenge(page):
            self._save_debug(page, project_id, "challenge_detected")
            return {"success": False, "project_id": project_id, "reason": "challenge_detected"}

        opened_bid_form = self._open_bid_form(page)
        if not opened_bid_form:
            self._save_debug(page, project_id, "bid_form_not_found")
            return {"success": False, "project_id": project_id, "reason": "bid_form_not_found"}

        amount_filled = self._fill_bid_amount(page, bid_amount)
        text_filled = self._fill_bid_text(page, proposal_text)

        if not amount_filled or not text_filled:
            self._save_debug(page, project_id, "form_fill_failed")
            return {
                "success": False,
                "project_id": project_id,
                "reason": f"form_fill_failed amount={amount_filled} text={text_filled}",
            }

        submit_locator = self._find_submit_button(page)
        if submit_locator is None:
            self._save_debug(page, project_id, "submit_button_not_found")
            return {"success": False, "project_id": project_id, "reason": "submit_button_not_found"}

        self._save_debug(page, project_id, "ready_to_submit")

        if dry_run:
            return {
                "success": False,
                "project_id": project_id,
                "reason": "ready_to_submit_manual_gate",
                "detail_url": detail_url,
                "dry_run": True,
            }

        try:
            submit_locator.click()
            page.wait_for_timeout(5000)
        except Exception as exc:
            self._save_debug(page, project_id, "submit_click_failed")
            return {"success": False, "project_id": project_id, "reason": f"submit_click_failed: {exc}"}

        self._save_debug(page, project_id, "after_submit_click")
        html = page.content().lower()
        success_markers = [
            "bid placed",
            "proposal submitted",
            "your bid has been placed",
            "edit your bid",
            "revoke bid",
        ]
        if any(marker in html for marker in success_markers):
            return {
                "success": True,
                "project_id": project_id,
                "reason": "submitted",
                "detail_url": detail_url,
                "dry_run": False,
            }

        return {
            "success": False,
            "project_id": project_id,
            "reason": "submit_clicked_but_confirmation_unclear",
            "detail_url": detail_url,
            "dry_run": False,
        }

    def _page_looks_like_challenge(self, page) -> bool:
        html = page.content().lower()
        markers = ["captcha", "verify you are human", "cloudflare", "attention required"]
        return any(marker in html for marker in markers)

    def _open_bid_form(self, page) -> bool:
        selectors = [
            'button:has-text("Bid on this Project")',
            'button:has-text("Place Bid")',
            'a:has-text("Bid on this Project")',
            'a:has-text("Place Bid")',
        ]
        for sel in selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                try:
                    locator.first.click()
                    page.wait_for_timeout(2500)
                    return True
                except Exception:
                    pass
        return False

    def _fill_bid_amount(self, page, amount: float) -> bool:
        selectors = [
            'input[name="bid"]',
            'input[name="amount"]',
            'input[inputmode="decimal"]',
            'input[type="number"]',
        ]
        for sel in selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                try:
                    locator.first.fill(str(amount))
                    return True
                except Exception:
                    pass
        return False

    def _fill_bid_text(self, page, proposal_text: str) -> bool:
        selectors = [
            'textarea[name="proposal"]',
            'textarea',
            '[contenteditable="true"]',
        ]
        for sel in selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                try:
                    if "contenteditable" in sel:
                        locator.first.click()
                        locator.first.fill(proposal_text)
                    else:
                        locator.first.fill(proposal_text)
                    return True
                except Exception:
                    pass
        return False

    def _find_submit_button(self, page):
        selectors = [
            'button:has-text("Submit Bid")',
            'button:has-text("Place Bid")',
            'button[type="submit"]',
        ]
        for sel in selectors:
            locator = page.locator(sel)
            if locator.count() > 0:
                return locator.first
        return None

    def _update_db_after_attempt(self, project_id: int, bid_id: int, result: dict, dry_run: bool) -> None:
        if result.get("success"):
            self.conn.execute("UPDATE projects SET status = 'BID_SUBMITTED' WHERE id = ?", (project_id,))
            self.conn.execute("UPDATE bid_drafts SET status = 'submitted' WHERE id = ?", (bid_id,))
        else:
            reason = result.get("reason", "unknown")
            if reason == "ready_to_submit_manual_gate":
                self.conn.execute("UPDATE projects SET status = 'NEEDS_HUMAN' WHERE id = ?", (project_id,))
                self.conn.execute("UPDATE bid_drafts SET status = 'ready_to_submit' WHERE id = ?", (bid_id,))
            else:
                self.conn.execute("UPDATE projects SET status = 'NEEDS_HUMAN' WHERE id = ?", (project_id,))
                self.conn.execute("UPDATE bid_drafts SET status = 'submit_failed' WHERE id = ?", (bid_id,))
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


def run(db_path: str = "freelance_hunter.db", limit: int = 3, headless: bool = False, dry_run: bool = True) -> list[dict]:
    submitter = FreelancerBidSubmitterV2(db_path=db_path)
    return submitter.run(limit=limit, headless=headless, dry_run=dry_run)
