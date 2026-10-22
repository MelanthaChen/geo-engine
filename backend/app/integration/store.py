from __future__ import annotations

from pathlib import Path
import json


class AppendOnlyJsonlStore:
    """Small local adapter store; records are never updated in place."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, record_type: str, record: dict) -> None:
        path = self.root / f"{record_type}.jsonl"
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    def records(self, record_type: str) -> list[dict]:
        path = self.root / f"{record_type}.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def find_profile(self, source_profile_id: str, source_profile_version: str) -> dict | None:
        return next((record for record in reversed(self.records("profile_import"))
                     if record.get("source_profile_id") == source_profile_id
                     and record.get("source_profile_version") == source_profile_version), None)
