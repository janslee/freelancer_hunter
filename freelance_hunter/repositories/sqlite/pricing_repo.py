from __future__ import annotations

from sqlite3 import Connection


class PricingRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    def save(self, project_id: int, pricing: dict) -> None:
        self.conn.execute(
            """
            INSERT INTO pricing_decisions (
                project_id, estimated_hours, floor_price, suggested_price,
                aggressive_price, premium_price, currency, strategy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                pricing["estimated_hours"],
                pricing["floor_price"],
                pricing["suggested_price"],
                pricing["aggressive_price"],
                pricing["premium_price"],
                pricing["currency"],
                pricing["strategy"],
            ),
        )
        self.conn.commit()

    def get_latest(self, project_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM pricing_decisions WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"No pricing decision found for project_id={project_id}")
        return dict(row)
