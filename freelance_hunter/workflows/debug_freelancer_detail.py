from __future__ import annotations

from pathlib import Path
import json
import yaml

from freelance_hunter.connectors.playwright_freelancer_detail import PlaywrightFreelancerDetailConnector


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run(detail_url: str) -> dict:
    platforms_cfg = _load_yaml(CONFIG_DIR / "platforms.yaml")
    freelancer_cfg = platforms_cfg.get("platforms", {}).get("freelancer", {})
    freelancer_cfg = {
        **freelancer_cfg,
        "headless": False,
        "session_dir": ".playwright/freelancer",
        "debug_dir": ".debug/freelancer",
    }

    connector = PlaywrightFreelancerDetailConnector(freelancer_cfg)
    project = connector.fetch_project_detail(detail_url.replace(freelancer_cfg.get('base_url', 'https://www.freelancer.com'), ''))
    return json.loads(project.model_dump_json())
