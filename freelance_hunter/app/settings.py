from __future__ import annotations

from pathlib import Path
import yaml


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_settings() -> dict:
    default_cfg = _load_yaml(CONFIG_DIR / "default.yaml")
    pricing_cfg = _load_yaml(CONFIG_DIR / "pricing.yaml")
    risk_cfg = _load_yaml(CONFIG_DIR / "risk_rules.yaml")
    return {
        **default_cfg,
        "pricing": pricing_cfg.get("pricing", {}),
        "risk": risk_cfg.get("risk", {}),
    }
