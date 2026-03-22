from __future__ import annotations

import json
from sqlite3 import Connection

from freelance_hunter.domain.models.project import ClientProfile, MoneyRange, Project


class ProjectRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    def save(self, project: Project) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO projects (
                platform, external_id, url, title, description, skills_json,
                currency, budget_min, budget_max, budget_type, bids_count,
                client_name, client_country, client_rating, payment_verified,
                raw_payload_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISCOVERED')
            """,
            (
                project.platform,
                project.external_id,
                project.url,
                project.title,
                project.description,
                json.dumps(project.skills, ensure_ascii=False),
                project.budget.currency,
                project.budget.min_amount,
                project.budget.max_amount,
                project.budget.amount_type,
                project.bids_count,
                project.client.name,
                project.client.country,
                project.client.rating,
                1 if project.client.payment_verified else 0,
                json.dumps(project.raw_payload, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def list_by_status(self, status: str) -> list[tuple[int, Project]]:
        rows = self.conn.execute(
            "SELECT * FROM projects WHERE status = ? ORDER BY id ASC", (status,)
        ).fetchall()
        return [(row["id"], self._row_to_project(row)) for row in rows]

    def update_status(self, project_id: int, status: str) -> None:
        self.conn.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
        self.conn.commit()

    def _row_to_project(self, row) -> Project:
        return Project(
            platform=row["platform"],
            external_id=row["external_id"],
            url=row["url"],
            title=row["title"],
            description=row["description"],
            skills=json.loads(row["skills_json"]),
            budget=MoneyRange(
                currency=row["currency"] or "USD",
                min_amount=row["budget_min"],
                max_amount=row["budget_max"],
                amount_type=row["budget_type"] or "fixed",
            ),
            bids_count=row["bids_count"],
            client=ClientProfile(
                name=row["client_name"],
                country=row["client_country"],
                rating=row["client_rating"],
                payment_verified=bool(row["payment_verified"]) if row["payment_verified"] is not None else None,
            ),
            raw_payload=json.loads(row["raw_payload_json"] or "{}"),
        )
