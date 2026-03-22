from __future__ import annotations

from freelance_hunter.domain.models.evaluation import EvaluationResult
from freelance_hunter.domain.models.project import Project


class ProjectScorer:
    def __init__(self, profile_cfg: dict, risk_cfg: dict):
        self.profile_cfg = profile_cfg
        self.risk_cfg = risk_cfg

    def evaluate(self, project: Project) -> EvaluationResult:
        skill = self._score_skill_match(project)
        profit = self._score_profit(project)
        clarity = self._score_clarity(project)
        client = self._score_client(project)
        reuse = self._score_reuse(project)
        risk = self._score_risk(project)

        overall = (
            skill * 0.35
            + profit * 0.25
            + client * 0.15
            + clarity * 0.10
            + reuse * 0.10
            - risk * 0.15
        )

        return EvaluationResult(
            project_key=f"{project.platform}:{project.external_id}",
            skill_match_score=round(skill, 2),
            profit_score=round(profit, 2),
            clarity_score=round(clarity, 2),
            client_quality_score=round(client, 2),
            reusability_score=round(reuse, 2),
            risk_score=round(risk, 2),
            overall_score=round(overall, 2),
            confidence=0.8,
            decision=self._decide(overall, risk, clarity),
            reasons=self._build_reasons(skill, profit, clarity, client, reuse, risk),
            unknowns=self._build_unknowns(),
        )

    def _score_skill_match(self, project: Project) -> float:
        preferred = set(s.lower() for s in self.profile_cfg.get("include_keywords", []))
        actual = set(s.lower() for s in project.skills)
        if not actual:
            return 40.0
        overlap = len(preferred & actual)
        return min(100.0, 40.0 + overlap * 15.0)

    def _score_profit(self, project: Project) -> float:
        min_budget = project.budget.min_amount or 0
        if min_budget >= 500:
            return 85.0
        if min_budget >= 300:
            return 70.0
        if min_budget >= 150:
            return 50.0
        return 20.0

    def _score_clarity(self, project: Project) -> float:
        text = (project.title + " " + project.description).lower()
        score = 40.0
        keywords = ["api", "dashboard", "admin", "deploy", "figma", "deadline", "database"]
        for kw in keywords:
            if kw in text:
                score += 8
        return min(score, 100.0)

    def _score_client(self, project: Project) -> float:
        score = 50.0
        if project.client.payment_verified:
            score += 20
        if project.client.rating and project.client.rating >= 4.5:
            score += 20
        return min(score, 100.0)

    def _score_reuse(self, project: Project) -> float:
        text = (project.title + " " + project.description).lower()
        reusable_keywords = ["dashboard", "admin", "crud", "cms", "internal tool", "management system"]
        score = 30.0
        for kw in reusable_keywords:
            if kw in text:
                score += 12
        return min(score, 100.0)

    def _score_risk(self, project: Project) -> float:
        text = (project.title + " " + project.description).lower()
        score = 10.0
        for kw in self.risk_cfg.get("high_risk_keywords", []):
            if kw.lower() in text:
                score += 30
        if (project.budget.min_amount or 0) < 100:
            score += 20
        return min(score, 100.0)

    def _decide(self, overall: float, risk: float, clarity: float) -> str:
        if risk >= 70:
            return "skip"
        if overall >= 75 and risk <= 25 and clarity >= 55:
            return "draft_bid"
        if overall >= 60:
            return "manual_review"
        return "skip"

    def _build_reasons(self, skill: float, profit: float, clarity: float, client: float, reuse: float, risk: float) -> list[str]:
        reasons: list[str] = []
        if skill >= 70:
            reasons.append("技能匹配度较高")
        if profit >= 70:
            reasons.append("预算处于可接受范围")
        if client >= 70:
            reasons.append("客户可信度较好")
        if clarity < 50:
            reasons.append("需求描述仍有不明确之处")
        if reuse >= 60:
            reasons.append("项目属于较高复用场景")
        if risk >= 40:
            reasons.append("项目存在一定风险，需要谨慎")
        return reasons

    def _build_unknowns(self) -> list[str]:
        return [
            "是否提供设计稿",
            "是否包含部署",
            "是否有明确验收标准",
        ]
