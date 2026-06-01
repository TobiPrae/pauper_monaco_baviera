"""Minimal persistent repo-scoped memory utilities.

Writes small JSON files under a workspace-local `.memories/repo/` directory.
This keeps repo memory alongside the project and avoids writing to root.
"""
from pathlib import Path
import json
from typing import Any, Optional


# Store workspace-scoped memory under the current working directory.
MEMORY_DIR = Path.cwd() / ".memories" / "repo"


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def save_fact(key: str, value: Any) -> None:
    """Save `value` under `key` as JSON in the repo memory folder."""
    _ensure_dir()
    path = MEMORY_DIR / f"{key}.json"
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def load_fact(key: str) -> Optional[Any]:
    """Load a previously saved fact by `key`. Returns None if missing."""
    path = MEMORY_DIR / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_facts() -> list[str]:
    _ensure_dir()
    return [p.stem for p in MEMORY_DIR.glob("*.json")]
