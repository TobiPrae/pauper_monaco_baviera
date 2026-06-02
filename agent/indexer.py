"""Repository indexer: lightweight AST-based symbol extraction.

Functions:
- build_index(root): walk Python files and return a mapping of file -> symbols
"""
from pathlib import Path
import ast
import json


def _extract_symbols(source: str):
    tree = ast.parse(source)
    symbols = {"functions": [], "classes": [], "imports": []}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            symbols["functions"].append(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols["classes"].append(node.name)
        elif isinstance(node, ast.Import):
            for n in node.names:
                symbols["imports"].append(n.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for n in node.names:
                symbols["imports"].append(f"{module}.{n.name}")
    return symbols


def build_index(root: str):
    """Build a simple index of Python files to their top-level symbols.

    Returns a dict suitable for serialization.
    """
    root_path = Path(root)
    index = {}
    for path in root_path.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
            symbols = _extract_symbols(text)
            index[str(path.relative_to(root_path))] = symbols
        except Exception:
            continue
    return index


def save_index(index: dict, out_path: str):
    Path(out_path).write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    idx = build_index(root)
    save_index(idx, "repo_index.json")
