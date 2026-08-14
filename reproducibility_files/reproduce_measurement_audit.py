#!/usr/bin/env python3
"""Reproduce rubric sensitivity, judge coverage, and score-method counts.

This script reads stored artifacts only. It performs no candidate, judge,
planner, or annotation inference.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


FROZEN_SUBTYPES = {
    "reaction_center_identification",
    "transformation_classification",
    "mechanistic_classification",
    "immediate_precursor_prediction",
    "immediate_precursor_with_disconnection",
    "reference_route_planning",
}
GROUP = {
    "immediate_precursor_prediction": "B1",
    "immediate_precursor_with_disconnection": "B2",
}
JUDGES = {
    "judge_gpt54mini": "GPT-5.4-mini",
    "judge_gemini31flashlite": "Gemini 3.1 Flash Lite",
    "judge_qwen36_35b_a3b": "Qwen3.6-35B-A3B",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key(row: dict) -> tuple[str, str, str]:
    return str(row["exam_id"]), str(row["page_id"]), str(row["question_id"])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rubric_sensitivity(repo: Path, stored: Path, outdir: Path) -> list[dict]:
    strict_rows = list(csv.DictReader((stored / "gpt54_b_strict_rubric_scores.csv").open(encoding="utf-8")))
    canonical_path = repo / "runs/benchmark_v3_gpt54_tools_no-sgr/gpt-5.4/judge_gpt54mini/llm_judge_output.jsonl"
    canonical = {key(row): row for row in read_jsonl(canonical_path)}
    values: dict[str, dict[str, list[float]]] = {
        "strict_reference_alignment": {"B1": [], "B2": []},
        "plausibility_oriented": {"B1": [], "B2": []},
    }
    for row in strict_rows:
        composite = (row["exam_id"], row["page_id"], row["question_id"])
        group = row["task_group"]
        values["strict_reference_alignment"][group].append(
            float(row["final_score"]) / float(row["max_score"])
        )
        current = canonical[composite]
        values["plausibility_oriented"][group].append(
            float(current["final_score"]) / float(current["max_score"])
        )
    if {group: len(rows) for group, rows in values["strict_reference_alignment"].items()} != {"B1": 210, "B2": 210}:
        raise RuntimeError("Strict-rubric artifact must contain 210 B1 and 210 B2 rows")
    output = []
    for rubric, grouped in values.items():
        b1 = sum(grouped["B1"]) / len(grouped["B1"]) * 100
        b2 = sum(grouped["B2"]) / len(grouped["B2"]) * 100
        output.append({"rubric": rubric, "B1_percent": round(b1, 3), "B2_percent": round(b2, 3), "B_mean_percent": round((b1 + b2) / 2, 3)})
    shift = output[1]["B_mean_percent"] - output[0]["B_mean_percent"]
    if abs(shift - 31.738) > 0.002:
        raise RuntimeError(f"Unexpected rubric shift: {shift}")
    for row in output:
        row["mean_shift_pp_vs_strict"] = round(row["B_mean_percent"] - output[0]["B_mean_percent"], 3)
    write_csv(output, outdir / "rubric_sensitivity.csv")
    return output


def coverage_and_methods(repo: Path, outdir: Path) -> tuple[list[dict], list[dict]]:
    benchmark = read_jsonl(repo / "benchmark/benchmark_v3_eval.jsonl")
    frozen_keys = {key(row) for row in benchmark if row.get("task_subtype") in FROZEN_SUBTYPES}
    if len(frozen_keys) != 773:
        raise RuntimeError(f"Expected 773 frozen keys, found {len(frozen_keys)}")
    paths = sorted(
        path for path in (repo / "runs").glob("**/judge_*/llm_judge_output.jsonl")
        if "repair_connection_errors" not in str(path)
    )
    if len(paths) != 48:
        raise RuntimeError(f"Expected 48 judge files, found {len(paths)}")
    manifest = []
    method_rows = []
    for path in paths:
        rows = read_jsonl(path)
        frozen = [row for row in rows if key(row) in frozen_keys]
        usable = [row for row in frozen if row.get("final_score") is not None]
        coverage = len(usable) / 773
        band = "ge95" if coverage >= 0.95 else "75_to_lt95" if coverage >= 0.75 else "50_to_lt75" if coverage >= 0.50 else "lt50"
        relative = str(path.relative_to(repo))
        manifest.append({"judge": JUDGES[path.parent.name], "path": relative, "sha256": sha256(path), "size_bytes": path.stat().st_size, "file_rows": len(rows), "frozen_usable_scores": len(usable), "frozen_coverage": f"{coverage:.6f}", "coverage_band": band})
        is_canonical = "no-sgr" in relative and path.parent.name == "judge_gpt54mini" and "gemma4" not in relative
        is_common = "benchmark_v3_gpt54_tools_sgr/gpt-5.4" in relative
        if is_canonical or is_common:
            counts = Counter(str(row.get("score_method") or "missing") for row in frozen)
            for method, count in sorted(counts.items()):
                method_rows.append({"analysis_set": "canonical no-SGR" if is_canonical else "GPT-5.4 SGR judge comparison", "judge": JUDGES[path.parent.name], "path": relative, "score_method": method, "rows": count})
    summary = []
    for judge in JUDGES.values():
        counts = Counter(row["coverage_band"] for row in manifest if row["judge"] == judge)
        summary.append({"judge": judge, "ge95": counts["ge95"], "75_to_lt95": counts["75_to_lt95"], "50_to_lt75": counts["50_to_lt75"], "lt50": counts["lt50"]})
    expected = {
        "GPT-5.4-mini": (8, 6, 0, 2),
        "Gemini 3.1 Flash Lite": (4, 2, 5, 5),
        "Qwen3.6-35B-A3B": (1, 4, 0, 11),
    }
    for row in summary:
        actual = tuple(row[name] for name in ("ge95", "75_to_lt95", "50_to_lt75", "lt50"))
        if actual != expected[row["judge"]]:
            raise RuntimeError(f"Coverage drift for {row['judge']}: {actual}")
    write_csv(manifest, outdir / "secondary_judge_coverage_inputs.csv")
    write_csv(summary, outdir / "secondary_judge_coverage_summary.csv")
    write_csv(method_rows, outdir / "score_method_taxonomy.csv")
    return summary, method_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--outdir", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    root = Path(__file__).resolve().parent
    stored = root / "stored_artifacts"
    outdir = (args.outdir or stored).resolve()
    rubric = rubric_sensitivity(repo, stored, outdir)
    coverage, methods = coverage_and_methods(repo, outdir)
    print(json.dumps({"rubric_sensitivity": rubric, "judge_coverage": coverage, "score_method_rows": len(methods)}, indent=2))


if __name__ == "__main__":
    main()
