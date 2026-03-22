from __future__ import annotations

from freelance_hunter.domain.models.project import Project


class ProposalGenerator:
    def generate_standard(self, project: Project, pricing: dict) -> dict:
        questions = [
            "Do you already have UI designs or wireframes?",
            "Should deployment be included in the scope?",
            "Do you have any preferred timeline or milestone structure?",
        ]

        amount = pricing["suggested_price"]
        currency = pricing["currency"]
        estimated_days = max(2, int(pricing["estimated_hours"] // 6))

        body = f"""
Hi,

I reviewed your project and I can help build this solution.

Based on the current description, I would approach it with a clean implementation focused on core functionality first, then testing and deployment support if needed.

Estimated timeline: {estimated_days} days
Proposed budget: {currency} {amount}

Before starting, I’d like to confirm:
- {questions[0]}
- {questions[1]}
- {questions[2]}

I have experience with similar web application and admin/dashboard style projects, and I can start quickly.

Best regards
""".strip()

        return {
            "style": "standard",
            "headline": f"I can help with {project.title}",
            "body": body,
            "questions": questions,
            "proposed_amount": amount,
            "currency": currency,
            "estimated_days": estimated_days,
        }
