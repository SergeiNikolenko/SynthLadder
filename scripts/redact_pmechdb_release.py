#!/usr/bin/env python3
"""Remove PMechDB-derived payloads from tracked release artifacts.

The script preserves identifiers, task metadata, execution status, score method,
and numeric scores needed for the published aggregate analysis. It removes
chemical inputs, reference answers, candidate answers, judge comments, and
verbose records for PMechDB rows. Full rows can be reconstructed only after a
user obtains PMechDB from its official distribution and accepts its terms.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PAYLOAD_FIELDS = {
    "answer_type",
    "agent_run_details",
    "benchmark_v3_gold",
    "benchmark_v3_input",
    "benchmark_v3_input_text",
    "canonical_answer",
    "gold",
    "input",
    "input_text",
    "judge_comment",
    "llm_comment",
    "question_text",
    "raw_answer",
    "reasoning_summary",
    "sgr_snapshot",
    "student_answer",
    "student_error",
    "trace_log_path",
}


def is_pmechdb(row: dict) -> bool:
    values = (
        row.get("source_id"),
        row.get("record_id"),
        row.get("benchmark_v3_record_id"),
        row.get("page_id"),
        row.get("question_id"),
    )
    return any("pmechdb" in str(value).lower() for value in values if value is not None)


def redact_row(row: dict) -> dict:
    if not is_pmechdb(row):
        return row
    redacted = dict(row)
    if "student_answer" in redacted:
        redacted["student_answer_present"] = bool(
            str(redacted.get("student_answer") or "").strip()
        )
    for field in PAYLOAD_FIELDS:
        redacted.pop(field, None)
    redacted["third_party_payload_redacted"] = "PMechDB"
    return redacted


def rewrite_jsonl(path: Path) -> tuple[int, int]:
    rows = []
    redacted_count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON in {path}:{line_number}") from exc
        if is_pmechdb(row):
            redacted_count += 1
        rows.append(redact_row(row))
    if redacted_count:
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
    return len(rows), redacted_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()
    files = sorted((repo / "benchmark").glob("*.jsonl"))
    files.extend(sorted((repo / "runs").glob("**/*.jsonl")))
    total = redacted = 0
    for path in files:
        rows, count = rewrite_jsonl(path)
        total += rows
        redacted += count
    print(f"processed_rows={total} redacted_pmechdb_rows={redacted}")


if __name__ == "__main__":
    main()
