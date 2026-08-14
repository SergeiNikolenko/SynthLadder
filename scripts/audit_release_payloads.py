#!/usr/bin/env python3
"""Fail if a tracked current-tree artifact exposes PMechDB-derived payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from redact_pmechdb_release import PAYLOAD_FIELDS, is_pmechdb


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()
    violations: list[str] = []
    checked = redacted = 0
    files = sorted((repo / "benchmark").glob("*.jsonl"))
    files.extend(sorted((repo / "runs").glob("**/*.jsonl")))
    for path in files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            checked += 1
            row = json.loads(line)
            if not is_pmechdb(row):
                continue
            redacted += 1
            present = sorted(PAYLOAD_FIELDS.intersection(row))
            if present:
                violations.append(
                    f"{path.relative_to(repo)}:{line_number}: payload fields {present}"
                )
            if row.get("third_party_payload_redacted") != "PMechDB":
                violations.append(
                    f"{path.relative_to(repo)}:{line_number}: missing redaction marker"
                )
    log_paths = [
        path.relative_to(repo)
        for path in (repo / "runs").glob("**/*")
        if path.is_file() and "pmechdb" in path.name.lower()
    ]
    violations.extend(f"PMechDB-named run artifact remains: {path}" for path in log_paths)
    if violations:
        raise SystemExit("\n".join(violations))
    print(f"checked_rows={checked} redacted_pmechdb_rows={redacted} violations=0")


if __name__ == "__main__":
    main()
