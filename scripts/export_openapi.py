import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path when running from CI or other contexts
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app import app  # noqa: E402


def main() -> None:
    schema = app.openapi()
    with open("openapi.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()