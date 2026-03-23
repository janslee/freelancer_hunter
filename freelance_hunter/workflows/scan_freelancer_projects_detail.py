from __future__ import annotations

from pathlib import Path
import yaml

from freelance_hunter.connectors.playwright_freelancer_detail import PlaywrightFreelancerDetailConnector
from freelance_hunter.repositories.sqlite.db import get_connection, init_db
from freelance_hunter.repositories.sqlite.project_repo import ProjectRepository


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run(db_path: str = "freelance_hunter.db", limit: int = 10, headless: bool = False) -> int:
    platforms_cfg = _load_yaml(CONFIG_DIR / "platforms.yaml")
    default_cfg = _load_yaml(CONFIG_DIR / "default.yaml")

    freelancer_cfg = platforms_cfg.get("platforms", {}).get("freelancer", {})
    freelancer_cfg = {
        **freelancer_cfg,
        "headless": headless,
        "session_dir": ".playwright/freelancer",
        "debug_dir": ".debug/freelancer",
    }
    keywords = default_cfg.get("filters", {}).get("include_keywords", [])

    conn = get_connection(db_path)
    init_db(conn)
    repo = ProjectRepository(conn)

    connector = PlaywrightFreelancerDetailConnector(freelancer_cfg)
    projects = connector.search_projects(keywords=keywords, limit=limit)

    for project in projects:
        repo.save(project)

    return len(projects)
