from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    project_key: str
    skill_match_score: float
    profit_score: float
    clarity_score: float
    client_quality_score: float
    reusability_score: float
    risk_score: float
    overall_score: float
    confidence: float
    decision: str
    reasons: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
