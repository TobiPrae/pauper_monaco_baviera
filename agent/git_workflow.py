"""Local git workflow helpers: prepare branch and patch commands (no auto-run).
"""
from pathlib import Path
import uuid


def branch_name(short_desc: str) -> str:
    safe = short_desc.strip().lower().replace(" ", "-")
    return f"agent/{safe}"[:100]


def prepare_branch_commands(branch: str) -> list[str]:
    return [f"git checkout -b {branch}", "# review changes", f"git add -A", f"git commit -m \"{branch}: changes from agent\""]


def write_patch(patch_text: str, out_dir: str = ".") -> str:
    out = Path(out_dir) / f"agent_patch_{uuid.uuid4().hex}.diff"
    out.write_text(patch_text, encoding="utf-8")
    return str(out)
