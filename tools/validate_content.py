from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "content"


def validate_json_files(root: Path) -> None:
    for path in sorted(root.rglob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    validate_json_files(CONTENT_ROOT)
    print("content validation passed")


if __name__ == "__main__":
    main()