"""CI guard (Task 4-2 Step 5, BR-4): no node under app/pipeline/ may hardcode
a prompt template string -- every node must call get_active_prompt() instead.

Heuristic: any string literal under app/pipeline/ (excluding the
app/pipeline/prompts/ package itself, which legitimately holds the seed
templates) that looks like a Jinja2 prompt template -- contains a
``{{ ... }}`` placeholder -- is flagged. A node inlining prompt text without
Jinja2 syntax would still be a smell, but the placeholder check is what
actually distinguishes "a prompt template" from an ordinary log message or
docstring without false-positiving on every long string in the codebase.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = ROOT / "backend" / "app" / "pipeline"
EXCLUDED_DIRS = {PIPELINE_DIR / "prompts"}

_JINJA_PLACEHOLDER = re.compile(r"\{\{\s*\w")


def _is_excluded(path: Path) -> bool:
    return any(excluded in path.parents or excluded == path for excluded in EXCLUDED_DIRS)


def find_hardcoded_prompts(pipeline_dir: Path = PIPELINE_DIR) -> list[tuple[str, int, str]]:
    """Return (file, line, snippet) for every offending string literal found."""
    offenses: list[tuple[str, int, str]] = []
    if not pipeline_dir.exists():
        return offenses

    for py_file in pipeline_dir.rglob("*.py"):
        if _is_excluded(py_file):
            continue
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _JINJA_PLACEHOLDER.search(node.value):
                    snippet = node.value.strip().splitlines()[0][:60]
                    try:
                        display_path = str(py_file.relative_to(ROOT))
                    except ValueError:
                        display_path = str(py_file)
                    offenses.append((display_path, node.lineno, snippet))
    return offenses


def main() -> int:
    offenses = find_hardcoded_prompts()
    if offenses:
        print(
            "Hardcoded prompt template(s) found under app/pipeline/ "
            "(nodes must call get_active_prompt() instead):",
            file=sys.stderr,
        )
        for file, line, snippet in offenses:
            print(f"  {file}:{line}: {snippet!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
