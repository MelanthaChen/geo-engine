#!/usr/bin/env python3
"""Local Phase 1 adapter; no network/provider work occurs unless audit is requested."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="GEO research integration v1 local adapter")
    parser.add_argument("--store", default=".integration-data", help="append-only JSONL store directory")
    sub = parser.add_subparsers(dest="command", required=True)
    import_parser = sub.add_parser("import-profile")
    import_parser.add_argument("profile", type=Path)
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("profile", type=Path, help="normalized profile JSON from import output")
    args = parser.parse_args()

    from app.core.database import SessionLocal
    from app.integration.adapter import GeoResearchIntegrationAdapter

    with args.profile.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    with SessionLocal() as db:
        adapter = GeoResearchIntegrationAdapter(db, args.store)
        if args.command == "import-profile":
            print(json.dumps(adapter.import_profile(payload), indent=2, sort_keys=True, default=str))
        else:
            print(json.dumps(adapter.run_read_only_audit(payload), indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
