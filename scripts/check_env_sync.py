"""Ensure Settings environment fields remain documented in .env.example."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import Settings  # noqa: E402


def example_keys() -> set[str]:
    """Return non-comment keys defined in the environment template."""

    return {
        line.split("=", 1)[0]
        for line in (ROOT / ".env.example").read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    }


def main() -> int:
    """Exit non-zero when a Settings field lacks template documentation."""

    missing = sorted(name.upper() for name in Settings.model_fields if name.upper() not in example_keys())
    if missing:
        print(f"Missing Settings keys in .env.example: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
