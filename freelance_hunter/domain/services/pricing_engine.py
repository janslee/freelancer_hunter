from __future__ import annotations

from freelance_hunter.domain.models.project import Project


class PricingEngine:
    def __init__(self, pricing_cfg: dict):
        self.cfg = pricing_cfg["pricing"] if "pricing" in pricing_cfg else pricing_cfg

    def estimate_hours(self, project: Project) -> float:
        text = (project.title + " " + project.description).lower()
        hours = 8.0
        if "dashboard" in text or "admin" in text:
            hours += 8
        if "api" in text:
            hours += 4
        if "auth" in text or "login" in text:
            hours += 3
        if "payment" in text:
            hours += 6
        if "deploy" in text:
            hours += 2
        return round(hours, 1)

    def calculate(self, project: Project) -> dict:
        hours = self.estimate_hours(project)
        currency = project.budget.currency or "USD"
        hourly_min = self.cfg["hourly_rate_min"][currency]
        hourly_target = self.cfg["hourly_rate_target"][currency]
        floor_price = hours * hourly_min
        suggested_price = hours * hourly_target
        aggressive_price = max(floor_price, suggested_price * 0.9)
        premium_price = suggested_price * 1.18
        return {
            "estimated_hours": round(hours, 1),
            "floor_price": round(floor_price, 2),
            "suggested_price": round(suggested_price, 2),
            "aggressive_price": round(aggressive_price, 2),
            "premium_price": round(premium_price, 2),
            "currency": currency,
            "strategy": "standard",
        }
