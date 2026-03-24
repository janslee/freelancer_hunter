from __future__ import annotations

from pathlib import Path
import json

from freelance_hunter.repositories.sqlite.db import get_connection, init_db


BASE_DIR = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = BASE_DIR / ".runtime" / "delivery_specs"


def run(project_id: int, db_path: str = "freelance_hunter.db") -> dict:
    conn = get_connection(db_path)
    init_db(conn)
    row = conn.execute(
        "SELECT id, title, description, url, platform FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Project {project_id} not found")

    title = row["title"]
    description = row["description"] or ""
    text = f"{title} {description}".lower()

    scope_items = []
    if "dashboard" in text or "admin" in text or "后台" in text:
        scope_items += ["Authentication", "Dashboard home", "Admin management pages"]
    if "api" in text or "接口" in text:
        scope_items += ["Backend API integration"]
    if "deploy" in text or "deployment" in text or "部署" in text:
        scope_items += ["Deployment support"]
    if not scope_items:
        scope_items = ["Core feature implementation", "Testing", "Delivery handoff"]

    spec = {
        "project_id": row["id"],
        "project_name": title,
        "platform": row["platform"],
        "source_url": row["url"],
        "objective": title,
        "scope_items": scope_items,
        "deliverables": [
            "Source code",
            "Basic technical documentation",
            "Deployment notes",
        ],
        "assumptions": [
            "One primary milestone structure",
            "Client provides missing assets when required",
        ],
        "unknowns": [
            "Final acceptance criteria",
            "Design availability",
            "Deployment environment details",
        ],
        "milestones": [
            {"name": "Scaffold and requirements alignment", "days": 1},
            {"name": "Core implementation", "days": 3},
            {"name": "Testing and delivery", "days": 1},
        ],
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACT_DIR / f"project_{project_id}.json"
    out_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec
