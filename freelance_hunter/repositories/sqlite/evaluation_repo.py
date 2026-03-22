from __future__ import annotations

import json
from sqlite3 import Connection

from freelance_hunter.domain.models.evaluation import EvaluationResult


class EvaluationRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    def save(self, project_id: int, evaluation: EvaluationResult) -> None:
        self.conn.execute(
            """
            INSERT INTO evaluations (
                project_id, project_key, skill_match_score, profit_score, clarity_score,
                client_quality_score, reusability_score, risk_score, overall_score,
                confidence, decision, reasons_json, unknowns_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                evaluation.project_key,
                evaluation.skill_match_score,
                evaluation.profit_score,
                evaluation.clarity_score,
                evaluation.client_quality_score,
                evaluation.reusability_score,
                evaluation.risk_score,
                evaluation.overall_score,
                evaluation.confidence,
                evaluation.decision,
                json.dumps(evaluation.reasons, ensure_ascii=False),
                json.dumps(evaluation.unknowns, ensure_ascii=False),
            ),
        )
        self.conn.commit()
