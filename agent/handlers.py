"""Action handlers: produce diffs, list tests, and prepare commands.
"""
from pathlib import Path
import difflib
import os
from typing import Dict, List, Tuple


def propose_patch(filename: str, original: str, new: str) -> str:
    """Return a unified diff patch for a single file.

    The returned string can be presented to the user for review.
    """
    orig_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, new_lines, fromfile=filename, tofile=filename)
    return "".join(diff)


def list_test_files(root: str) -> List[str]:
    p = Path(root)
    return [str(x.relative_to(p)) for x in p.rglob("test_*.py")] + [str(x.relative_to(p)) for x in p.rglob("*_test.py")]


def prepare_run_tests_command(extra_args: str = "") -> str:
    cmd = f"pytest {extra_args}".strip()
    return cmd


def prepare_format_command(paths: List[str]) -> str:
    joined = " ".join(paths)
    return f"black {joined} && flake8 {joined}"


def propose_patches_for_files(files: Dict[str, Tuple[str, str]]) -> str:
    """Given a mapping filename -> (original, new) return a combined unified diff.

    `files` should be a dict where each value is a (original_text, new_text) tuple.
    """
    parts: List[str] = []
    for filename, (orig, new) in files.items():
        parts.append(propose_patch(str(filename), orig, new))
    return "\n".join(parts)

