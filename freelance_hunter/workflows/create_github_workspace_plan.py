from __future__ import annotations

from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = BASE_DIR / ".runtime" / "delivery_specs"
PLAN_DIR = BASE_DIR / ".runtime" / "github_workspace_plans"


def run(project_id: int) -> dict:
    spec_path = ARTIFACT_DIR / f"project_{project_id}.json"
    if not spec_path.exists():
        raise ValueError(f"Delivery spec for project {project_id} not found. Generate it first.")

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    repo_name = f"client-project-{project_id}"
    plan = {
        "project_id": project_id,
        "repo_name": repo_name,
        "repo_description": spec.get("project_name", "Client project workspace"),
        "issues": [
            "Project scaffold",
            "Requirements clarification",
            "Database/API design",
            "Core feature implementation",
            "Testing and QA",
            "Deployment and handoff",
        ],
        "milestones": [m["name"] for m in spec.get("milestones", [])],
        "readme_outline": [
            "Project overview",
            "Setup instructions",
            "Milestones",
            "Open questions",
        ],
    }

    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PLAN_DIR / f"project_{project_id}.json"
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan
