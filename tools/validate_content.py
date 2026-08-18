from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.content.validator import ContentValidator, REQUIRED_CONTENT_TYPES

CONTENT_ROOT = ROOT / "content"


def validate_json_files(root: Path) -> None:
    for path in sorted(root.rglob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))


def load_content_pack(pack_dir: Path) -> tuple[dict[str, object], str]:
    manifest_path = pack_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pack = {
        content_type: json.loads((pack_dir / f"{content_type}.json").read_text(encoding="utf-8"))
        for content_type in REQUIRED_CONTENT_TYPES
    }
    impact_notes = str(manifest.get("impact_notes", ""))
    pack["content_pack_name"] = str(manifest.get("content_pack_name", pack_dir.name))
    pack["author_id"] = str(manifest.get("author_id", "system"))
    return pack, impact_notes


def main() -> None:
    validate_json_files(CONTENT_ROOT)
    validator = ContentValidator()
    packs_root = CONTENT_ROOT / "packs"
    errors: list[str] = []
    warnings: list[str] = []

    for pack_dir in sorted(path for path in packs_root.iterdir() if path.is_dir()):
        content_pack, impact_notes = load_content_pack(pack_dir)
        pack_errors, pack_warnings = validator.validate_content_pack(content_pack, impact_notes)
        errors.extend(f"{pack_dir.name}: {message}" for message in pack_errors)
        warnings.extend(f"{pack_dir.name}: {message}" for message in pack_warnings)

    if errors or warnings:
        details = "\n".join([*errors, *warnings])
        issue_labels: list[str] = []
        if errors:
            issue_labels.append("errors")
        if warnings:
            issue_labels.append("warnings")
        raise SystemExit(f"content validation failed with {' and '.join(issue_labels)}\n{details}")
    print("content validation passed")


if __name__ == "__main__":
    main()