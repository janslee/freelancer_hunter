from __future__ import annotations

import json
from pathlib import Path

import yaml

from freelance_hunter.connectors.freelancer import FreelancerConnector


def load_platform_cfg() -> dict:
    config_path = Path(__file__).resolve().parents[2] / "config" / "platforms.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("platforms", {}).get("freelancer", {})


def main() -> None:
    cfg = load_platform_cfg()
    connector = FreelancerConnector(cfg)
    projects = connector.search_projects(["react", "java", "dashboard"], limit=10)
    print(json.dumps([p.model_dump() for p in projects], ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
