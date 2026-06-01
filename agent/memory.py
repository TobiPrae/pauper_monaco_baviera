"""Minimal persistent repo-scoped memory utilities.

Writes small JSON files under the workspace `/memories/repo/` directory.
"""
from pathlib import Path
import json


MEMORY_DIR = Path("/memories/repo")


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def save_fact(key: str, value):
    _ensure_dir()
    path = MEMORY_DIR / f"{key}.json"
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def load_fact(key: str):
    path = MEMORY_DIR / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_facts():
    _ensure_dir()
    return [p.stem for p in MEMORY_DIR.glob("*.json")]
