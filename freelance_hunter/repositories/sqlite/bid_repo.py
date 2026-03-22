from __future__ import annotations

import json
from sqlite3 import Connection


class BidRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    def save(self, project_id: int, bid: dict) -> None:
        self.conn.execute(
            """
            INSERT INTO bid_drafts (
                project_id, style, headline, body, questions_json,
                proposed_amount, currency, estimated_days, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            """,
            (
                project_id,
                bid["style"],
                bid["headline"],
                bid["body"],
                json.dumps(bid["questions"], ensure_ascii=False),
                bid["proposed_amount"],
                bid["currency"],
                bid["estimated_days"],
            ),
        )
        self.conn.commit()
