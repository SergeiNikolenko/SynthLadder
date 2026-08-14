#!/usr/bin/env python3
"""Reproduce the SynthLadder manuscript analyses from stored artifacts.

The script performs no candidate-model, judge-model, planner, or chemist-label
inference. It validates the frozen benchmark and stored rows, classifies
candidate-side and judge-side failures, applies the declared provenance
correction, and recomputes all manuscript score summaries.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
import sys
from collections import Counter
from pathlib import Path
import numpy as np

from reproduce_measurement_audit import coverage_and_methods, rubric_sensitivity


TASK_GROUPS = {
    "reaction_center_identification": "A1a",
    "transformation_classification": "A1b",
    "mechanistic_classification": "A2",
    "immediate_precursor_prediction": "B1",
    "immediate_precursor_with_disconnection": "B2",
    "reference_route_planning": "C",
}

EXPECTED_TASK_COUNTS = {
    "A1a": 76,
    "A1b": 64,
    "A2": 76,
    "B1": 210,
    "B2": 210,
    "C": 137,
}

RUNS = {
    "GPT-5.4": "runs/benchmark_v3_gpt54_tools_no-sgr/gpt-5.4",
    "GPT-5.4-mini": "runs/benchmark_v3_gpt54mini_tools_no-sgr/gpt-5.4-mini",
    "Gemini 3.1 Pro": "runs/benchmark_v3_gemini31pro_minimal_no-sgr",
    "GLM-5.1": "runs/benchmark_v3_glm51_minimal_no-sgr",
    "Gemini 3 Flash": "runs/benchmark_v3_gemini3flash_minimal_no-sgr",
    "Qwen3.6-35B-A3B": "runs/benchmark_v3_qwen36_35b_a3b_minimal_no-sgr",
    "GPT-OSS": "runs/benchmark_v3_gptoss_tools_no-sgr",
}

CANONICAL_JUDGE = "judge_gpt54mini/llm_judge_output.jsonl"
STUDENT_OUTPUT = "student_output.jsonl"

COMMON_ITEM_JUDGES = {
    "GPT-5.4-mini": (
        "runs/benchmark_v3_gpt54_tools_sgr/gpt-5.4/"
        "judge_gpt54mini/llm_judge_output.jsonl"
    ),
    "Gemini 3.1 Flash Lite": (
        "runs/benchmark_v3_gpt54_tools_sgr/gpt-5.4/"
        "judge_gemini31flashlite/llm_judge_output.jsonl"
    ),
    "Qwen3.6-35B-A3B": (
        "runs/benchmark_v3_gpt54_tools_sgr/gpt-5.4/"
        "judge_qwen36_35b_a3b/llm_judge_output.jsonl"
    ),
}

EXPECTED_SUITE_MACRO = {
    "GPT-5.4": 68.2,
    "GPT-5.4-mini": 66.1,
    "Gemini 3.1 Pro": 59.2,
    "GLM-5.1": 56.9,
    "Gemini 3 Flash": 50.9,
    "Qwen3.6-35B-A3B": 26.8,
    "GPT-OSS": 12.4,
}


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON in {path}:{line_number}") from exc
    return rows


def item_key(row: dict) -> tuple[str, str, str]:
    return str(row["exam_id"]), str(row["page_id"]), str(row["question_id"])


def keyed_rows(path: Path, *, expected_rows: int | None = None) -> dict[tuple[str, str, str], dict]:
    rows = read_jsonl(path)
    keys = [item_key(row) for row in rows]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise RuntimeError(f"Duplicate composite keys in {path}: {duplicates[:5]}")
    if expected_rows is not None and len(rows) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} rows in {path}, found {len(rows)}")
    return dict(zip(keys, rows, strict=True))


def frozen_items(repo: Path) -> list[dict]:
    source = repo / "benchmark/benchmark_v3_eval.jsonl"
    all_rows = keyed_rows(source, expected_rows=990)
    rows = [row for row in all_rows.values() if row.get("task_subtype") in TASK_GROUPS]
    keys = [item_key(row) for row in rows]
    if len(rows) != 773 or len(set(keys)) != 773:
        raise RuntimeError(f"Expected 773 unique core rows, found {len(rows)}")
    counts = Counter(TASK_GROUPS[row["task_subtype"]] for row in rows)
    if dict(counts) != EXPECTED_TASK_COUNTS:
        raise RuntimeError(f"Unexpected frozen task composition: {dict(counts)}")
    return rows


def contaminated_mini_rows(repo: Path) -> tuple[set[tuple[str, str, str]], list[dict]]:
    path = (
        repo
        / "runs/benchmark_v3_gpt54mini_tools_no-sgr/gpt-5.4-mini/"
        "rescue_provenance.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    keys: set[tuple[str, str, str]] = set()
    rows: list[dict] = []
    for row in payload["replaced_rows"]:
        key = tuple(row["key"].split("/"))
        if len(key) != 3:
            raise RuntimeError(f"Invalid replacement key: {row['key']}")
        keys.add(key)
        rows.append(row)
    if len(rows) != 27 or len(keys) != 27:
        raise RuntimeError(f"Expected 27 unique replaced rows, found {len(rows)}")
    return keys, rows


def write_mini_provenance(repo: Path, destination: Path) -> None:
    _, source_rows = contaminated_mini_rows(repo)
    payload_path = (
        repo
        / "runs/benchmark_v3_gpt54mini_tools_no-sgr/gpt-5.4-mini/"
        "rescue_provenance.json"
    )
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for row in source_rows:
        exam_id, page_id, question_id = row["key"].split("/")
        rows.append(
            {
                "exam_id": exam_id,
                "page_id": page_id,
                "question_id": question_id,
                "source_model": row.get("rescue_model_inferred", "gpt-5.4"),
                "source_run": row.get(
                    "rescue_source_path", payload.get("second_pass_source_run")
                ),
                "cross_model_rescue": row.get("cross_model_rescue", True),
                "corrective_score": 0,
            }
        )
    write_csv(rows, destination)


def validate_score(row: dict, item: dict, path: Path) -> float | None:
    final = row.get("final_score")
    if final is None:
        return None
    maximum = float(row.get("max_score") or item["max_score"])
    score = float(final)
    if not math.isfinite(score) or not math.isfinite(maximum) or maximum <= 0:
        raise RuntimeError(f"Non-finite score or maximum in {path}: {item_key(row)}")
    if score < 0 or score > maximum:
        raise RuntimeError(
            f"Score outside [0, max_score] in {path}: {item_key(row)} = {score}/{maximum}"
        )
    return score / maximum


def load_run_rows(
    repo: Path, model: str
) -> tuple[dict[tuple[str, str, str], dict], dict[tuple[str, str, str], dict], Path, Path]:
    run_root = repo / RUNS[model]
    student_path = run_root / STUDENT_OUTPUT
    judge_path = run_root / CANONICAL_JUDGE
    students = keyed_rows(student_path, expected_rows=990)
    judged = keyed_rows(judge_path, expected_rows=990)
    return students, judged, student_path, judge_path


def score_vectors(
    repo: Path, model: str, items: list[dict]
) -> tuple[dict[str, np.ndarray], dict[str, object], list[Path]]:
    students, judged, student_path, judge_path = load_run_rows(repo, model)
    zero_keys, _ = contaminated_mini_rows(repo) if model == "GPT-5.4-mini" else (set(), [])
    frozen_keys = {item_key(item) for item in items}
    if not frozen_keys.issubset(students) or not frozen_keys.issubset(judged):
        raise RuntimeError(f"Stored run does not contain every frozen key: {model}")
    if zero_keys - frozen_keys:
        raise RuntimeError("Replacement provenance contains keys outside the frozen analysis")

    vectors: dict[str, list[float]] = {name: [] for name in EXPECTED_TASK_COUNTS}
    candidate_statuses: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    for item in items:
        key = item_key(item)
        student = students[key]
        judge = judged[key]
        answer = str(student.get("student_answer") or "").strip()
        answer_present = bool(answer) or bool(student.get("student_answer_present"))
        status = str(student.get("student_status") or "not_recorded")
        candidate_statuses[status] += 1
        normalized = validate_score(judge, item, judge_path)
        contaminated = key in zero_keys

        candidate_failed = status != "ok" or not answer_present
        judge_missing_after_answer = answer_present and normalized is None
        if not answer_present and normalized is not None:
            raise RuntimeError(f"Empty candidate answer received a score: {model} {key}")

        counts["candidate_error"] += int(candidate_failed)
        counts["candidate_empty"] += int(not answer_present)
        counts["judge_missing_after_nonempty_answer"] += int(judge_missing_after_answer)
        counts["cross_model_replacement"] += int(contaminated)
        counts["usable_stored_score"] += int(normalized is not None)
        counts["native_scored_row"] += int(normalized is not None and not contaminated)

        score = 0.0
        if normalized is not None and not contaminated:
            score = normalized
        vectors[TASK_GROUPS[item["task_subtype"]]].append(score)

    report: dict[str, object] = {
        "system_configuration": model,
        "frozen_rows": len(items),
        "candidate_error_rows": counts["candidate_error"],
        "candidate_empty_rows": counts["candidate_empty"],
        "judge_missing_after_nonempty_answer": counts["judge_missing_after_nonempty_answer"],
        "cross_model_replacement_rows": counts["cross_model_replacement"],
        "usable_stored_scores": counts["usable_stored_score"],
        "native_scored_rows": counts["native_scored_row"],
        "candidate_status_counts": "; ".join(
            f"{name}={count}" for name, count in sorted(candidate_statuses.items())
        ),
    }
    arrays = {name: np.asarray(values, dtype=float) for name, values in vectors.items()}
    for name, expected in EXPECTED_TASK_COUNTS.items():
        if len(arrays[name]) != expected:
            raise RuntimeError(f"Unexpected {name} length for {model}: {len(arrays[name])}")
    return arrays, report, [student_path, judge_path]


def estimates(vectors: dict[str, np.ndarray]) -> dict[str, float]:
    a1 = np.concatenate((vectors["A1a"], vectors["A1b"]))
    a = np.concatenate((a1, vectors["A2"]))
    b = np.concatenate((vectors["B1"], vectors["B2"]))
    all_items = np.concatenate(tuple(vectors[name] for name in EXPECTED_TASK_COUNTS))
    result = {name: float(values.mean()) for name, values in vectors.items()}
    result["A1"] = float(a1.mean())
    result["A"] = float(a.mean())
    result["B"] = float(b.mean())
    result["SuiteMacro"] = float(np.mean((result["A"], result["B"], result["C"])))
    result["Micro773"] = float(all_items.mean())
    result["SubtypeMacro6"] = float(
        np.mean(tuple(result[name] for name in EXPECTED_TASK_COUNTS))
    )
    return result


METRICS = (
    "SuiteMacro",
    "Micro773",
    "SubtypeMacro6",
    "A",
    "A1",
    "A1a",
    "A1b",
    "A2",
    "B",
    "B1",
    "B2",
    "C",
)


def bootstrap(
    vectors: dict[str, np.ndarray], *, draws: int, seed: int
) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {name: [] for name in METRICS}
    for _ in range(draws):
        resampled = {
            name: values[rng.integers(0, len(values), len(values))]
            for name, values in vectors.items()
        }
        current = estimates(resampled)
        for name in samples:
            samples[name].append(current[name])
    return {
        name: tuple(float(x) for x in np.percentile(values, [2.5, 97.5]))
        for name, values in samples.items()
    }


def paired_bootstrap(
    first: dict[str, np.ndarray],
    second: dict[str, np.ndarray],
    *,
    draws: int,
    seed: int,
) -> dict[str, float | int | str]:
    rng = np.random.default_rng(seed)
    differences: list[float] = []
    for _ in range(draws):
        indices = {
            name: rng.integers(0, len(first[name]), len(first[name]))
            for name in EXPECTED_TASK_COUNTS
        }
        first_sample = {name: first[name][indices[name]] for name in indices}
        second_sample = {name: second[name][indices[name]] for name in indices}
        differences.append(
            estimates(first_sample)["SuiteMacro"] - estimates(second_sample)["SuiteMacro"]
        )
    point = estimates(first)["SuiteMacro"] - estimates(second)["SuiteMacro"]
    low, high = np.percentile(differences, [2.5, 97.5])
    return {
        "comparison": "GPT-5.4 minus GPT-5.4-mini",
        "metric": "SuiteMacro",
        "difference_pp": round(point * 100, 3),
        "ci95_low_pp": round(float(low) * 100, 3),
        "ci95_high_pp": round(float(high) * 100, 3),
        "bootstrap_draws": draws,
        "seed": seed,
        "uncertainty_scope": "paired item resampling within six task subtypes",
    }


def average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2 + 1
        start = end
    return ranks


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return pearson(average_ranks(x), average_ranks(y))


def kendall_tau_b(x: np.ndarray, y: np.ndarray) -> float:
    concordant = discordant = ties_x = ties_y = 0
    for i in range(len(x) - 1):
        for j in range(i + 1, len(x)):
            dx = np.sign(x[j] - x[i])
            dy = np.sign(y[j] - y[i])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx == dy:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt(
        (concordant + discordant + ties_x) * (concordant + discordant + ties_y)
    )
    if denominator == 0:
        return float("nan")
    return (concordant - discordant) / denominator


def pair_statistics(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    return {
        "pearson_r": pearson(x, y),
        "spearman_rho": spearman(x, y),
        "kendall_tau_b": kendall_tau_b(x, y),
        "mean_difference_pp": float(np.mean(x - y) * 100),
        "mae_pp": float(np.mean(np.abs(y - x)) * 100),
    }


def bootstrap_pair_statistics(
    x: np.ndarray, y: np.ndarray, *, draws: int, seed: int
) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    names = ("pearson_r", "spearman_rho", "mean_difference_pp", "mae_pp")
    samples: dict[str, list[float]] = {name: [] for name in names}
    for _ in range(draws):
        indices = rng.integers(0, len(x), len(x))
        sampled_x = x[indices]
        sampled_y = y[indices]
        current = {
            "pearson_r": pearson(sampled_x, sampled_y),
            "spearman_rho": spearman(sampled_x, sampled_y),
            "mean_difference_pp": float(np.mean(sampled_x - sampled_y) * 100),
            "mae_pp": float(np.mean(np.abs(sampled_y - sampled_x)) * 100),
        }
        for name in names:
            if math.isfinite(current[name]):
                samples[name].append(current[name])
    return {
        name: tuple(float(v) for v in np.percentile(values, [2.5, 97.5]))
        for name, values in samples.items()
        if values
    }


def judge_item_statistics(
    repo: Path, items: list[dict], *, draws: int, seed: int
) -> tuple[list[dict[str, object]], list[Path]]:
    judges: dict[str, dict[tuple[str, str, str], dict]] = {}
    paths: list[Path] = []
    for name, relative in COMMON_ITEM_JUDGES.items():
        path = repo / relative
        judges[name] = keyed_rows(path, expected_rows=990)
        paths.append(path)

    item_by_key = {item_key(item): item for item in items}
    pairs = [
        ("GPT-5.4-mini", "Gemini 3.1 Flash Lite"),
        ("GPT-5.4-mini", "Qwen3.6-35B-A3B"),
        ("Gemini 3.1 Flash Lite", "Qwen3.6-35B-A3B"),
    ]
    records: list[dict[str, object]] = []
    row_index = 0
    for group in EXPECTED_TASK_COUNTS:
        group_keys = [
            key
            for key, item in item_by_key.items()
            if TASK_GROUPS[item["task_subtype"]] == group
        ]
        for first_name, second_name in pairs:
            first_values: list[float] = []
            second_values: list[float] = []
            for key in group_keys:
                first_row = judges[first_name][key]
                second_row = judges[second_name][key]
                first = validate_score(first_row, item_by_key[key], repo / COMMON_ITEM_JUDGES[first_name])
                second = validate_score(second_row, item_by_key[key], repo / COMMON_ITEM_JUDGES[second_name])
                if first is None or second is None:
                    continue
                first_values.append(first)
                second_values.append(second)
            x = np.asarray(first_values, dtype=float)
            y = np.asarray(second_values, dtype=float)
            if len(x) < 3:
                raise RuntimeError(f"Insufficient common judge scores for {group}: {first_name}/{second_name}")
            point = pair_statistics(x, y)
            intervals = bootstrap_pair_statistics(x, y, draws=draws, seed=seed + row_index)
            record: dict[str, object] = {
                "candidate_answer_set": "GPT-5.4 SGR",
                "task_group": group,
                "first_judge": first_name,
                "second_judge": second_name,
                "common_items_n": len(x),
            }
            for name, value in point.items():
                record[name] = round(value, 4)
                if name in intervals:
                    low, high = intervals[name]
                    record[f"{name}_ci95_low"] = round(low, 4)
                    record[f"{name}_ci95_high"] = round(high, 4)
            records.append(record)
            row_index += 1
    return records, paths


def sequential_atom_map_rows(items: list[dict]) -> list[dict[str, object]]:
    """Classify B2 targets whose atom-map labels appear exactly as 1..N in SMILES order."""
    rows: list[dict[str, object]] = []
    for item in items:
        if TASK_GROUPS[item["task_subtype"]] != "B2":
            continue
        target = str(item.get("benchmark_v3_input", {}).get("target") or "")
        labels = [int(value) for value in re.findall(r":(\d+)\]", target)]
        expected = list(range(1, len(labels) + 1))
        rows.append(
            {
                "exam_id": item["exam_id"],
                "page_id": item["page_id"],
                "question_id": item["question_id"],
                "atom_count": len(labels),
                "atom_map_labels_in_smiles_order": " ".join(map(str, labels)),
                "sequential_1_to_n_in_smiles_order": labels == expected,
            }
        )
    if len(rows) != 210 or sum(bool(row["sequential_1_to_n_in_smiles_order"]) for row in rows) != 186:
        raise RuntimeError("Expected 186 of 210 B2 targets with sequential atom-map labels")
    return rows


def excluded_rows(items_path: Path) -> list[dict[str, object]]:
    rows = read_jsonl(items_path)
    counts = Counter(row.get("task_subtype") for row in rows if row.get("task_subtype") not in TASK_GROUPS)
    expected = {"reagent_role_identification": 112, "condition_role_identification": 92, "route_design": 13}
    if dict(counts) != expected:
        raise RuntimeError(f"Unexpected excluded-row composition: {dict(counts)}")
    reason = {
        "reagent_role_identification": "auxiliary procedure-grounding task outside the six frozen analysis subtypes",
        "condition_role_identification": "auxiliary procedure-grounding task outside the six frozen analysis subtypes",
        "route_design": "internal pilot task outside the frozen reference-route analysis",
    }
    return [
        {"task_subtype": name, "rows": count, "exclusion_reason": reason[name]}
        for name, count in expected.items()
    ]


def sensitivity_rows(repo: Path, items: list[dict]) -> list[dict[str, object]]:
    """Recompute end-to-end, native-output complete-case, and rescue-inclusive suite macros."""
    result: list[dict[str, object]] = []
    for model in RUNS:
        students, judged, _, judge_path = load_run_rows(repo, model)
        replacement_keys, _ = contaminated_mini_rows(repo) if model == "GPT-5.4-mini" else (set(), [])
        end_to_end: dict[str, list[float]] = {name: [] for name in EXPECTED_TASK_COUNTS}
        native: dict[str, list[float]] = {name: [] for name in EXPECTED_TASK_COUNTS}
        rescue_inclusive: dict[str, list[float]] = {name: [] for name in EXPECTED_TASK_COUNTS}
        for item in items:
            key = item_key(item)
            group = TASK_GROUPS[item["task_subtype"]]
            student = students[key]
            answer = str(student.get("student_answer") or "").strip()
            answer_present = bool(answer) or bool(student.get("student_answer_present"))
            status = str(student.get("student_status") or "not_recorded")
            normalized = validate_score(judged[key], item, judge_path)
            candidate_failed = status != "ok" or not answer_present or normalized is None
            replacement = key in replacement_keys
            end_to_end[group].append(0.0 if candidate_failed or replacement else float(normalized))
            rescue_inclusive[group].append(0.0 if candidate_failed else float(normalized))
            if not candidate_failed and not replacement:
                native[group].append(float(normalized))
        def suite_macro(values: dict[str, list[float]]) -> float:
            a = np.mean(values["A1a"] + values["A1b"] + values["A2"])
            b = np.mean(values["B1"] + values["B2"])
            c = np.mean(values["C"])
            return float(np.mean((a, b, c)) * 100)
        result.append(
            {
                "system_configuration": model,
                "end_to_end_suite_macro_percent": round(suite_macro(end_to_end), 3),
                "native_output_complete_case_suite_macro_percent": round(suite_macro(native), 3),
                "rescue_inclusive_suite_macro_percent": (
                    round(suite_macro(rescue_inclusive), 3) if model == "GPT-5.4-mini" else None
                ),
                "native_output_denominator_note": "suite means recomputed after removing candidate failures and cross-configuration replacements within each suite",
            }
        )
    return result


def human_annotation_summary(root: Path) -> list[dict[str, object]]:
    label_paths = [root / "human_labels_daniil_63.jsonl", root / "human_labels_mark_63.jsonl"]
    labels = [{str(row["key"]): int(row["human_score_0_10"]) for row in read_jsonl(path)} for path in label_paths]
    if set(labels[0]) != set(labels[1]) or len(labels[0]) != 63:
        raise RuntimeError("Human label files must contain the same 63 keys")
    subset = {}
    with (root / "human_validation_subset.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = row["key"]
            subset[key] = "A1b" if row["task_subtype"] == "transformation_classification" else "B1"

    def quadratic_weighted_kappa(keys: list[str]) -> float:
        categories = [0, 2, 4, 6, 8, 10]
        category_index = {value: index for index, value in enumerate(categories)}
        observed = np.zeros((len(categories), len(categories)), dtype=float)
        for key in keys:
            observed[category_index[labels[0][key]], category_index[labels[1][key]]] += 1
        expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / observed.sum()
        weights = np.fromfunction(
            lambda first, second: ((first - second) / (len(categories) - 1)) ** 2,
            observed.shape,
        )
        return float(1 - np.sum(weights * observed) / np.sum(weights * expected))

    records: list[dict[str, object]] = []
    for group in ("A1b", "B1", "Overall"):
        keys = sorted(labels[0]) if group == "Overall" else sorted(key for key in labels[0] if subset[key] == group)
        differences = np.asarray([abs(labels[0][key] - labels[1][key]) for key in keys], dtype=float)
        records.append(
            {
                "selected_task": group,
                "n": len(keys),
                "exact_agreement_n": int(np.sum(differences == 0)),
                "within_two_points_n": int(np.sum(differences <= 2)),
                "mean_absolute_difference": round(float(np.mean(differences)), 3),
                "quadratic_weighted_cohen_kappa": round(quadratic_weighted_kappa(keys), 3),
            }
        )
    expected = [("A1b", 41, 33, 39), ("B1", 22, 9, 15), ("Overall", 63, 42, 54)]
    if [(r["selected_task"], r["n"], r["exact_agreement_n"], r["within_two_points_n"]) for r in records] != expected:
        raise RuntimeError("Human annotation summary drift")
    return records


def environment_record(repo: Path) -> dict[str, object]:
    lockfile = repo / "uv.lock"
    return {
        "source_artifact_commit": "38a82d59474ea131747aff7b1977bb0393fd2af4",
        "release_tree_note": "PMechDB payload-redacted publication tree; identify by the public commit cited in the manuscript",
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "dependency_lockfile": "uv.lock",
        "dependency_lockfile_sha256": sha256(lockfile),
        "reproduction_command": "uv run --project /path/to/SynthLadder --frozen python reproducibility_files/reproduce_scores.py --repo /path/to/SynthLadder --outdir reproducibility_files/generated",
    }


def write_manifest(items: list[dict], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for row in items:
            payload = {
                "exam_id": row["exam_id"],
                "page_id": row["page_id"],
                "question_id": row["question_id"],
                "benchmark_suite": row["benchmark_suite"],
                "benchmark_subtrack": row["benchmark_subtrack"],
                "analysis_task_group": TASK_GROUPS[row["task_subtype"]],
                "task_subtype": row["task_subtype"],
                "source_id": row.get("source_id"),
                "source_split": row.get("source_split"),
                "max_score": row["max_score"],
            }
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(rows: list[dict], destination: Path) -> None:
    if not rows:
        raise RuntimeError(f"Refusing to write empty table: {destination}")
    fieldnames: list[str] = []
    for row in rows:
        for name in row:
            if name not in fieldnames:
                fieldnames.append(name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {
                name: "" if isinstance(value, float) and not math.isfinite(value) else value
                for name, value in row.items()
            }
            for row in rows
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(paths: set[Path], repo: Path, destination: Path) -> None:
    rows = [
        {
            "path": str(path.resolve().relative_to(repo.resolve())),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(paths)
    ]
    write_csv(rows, destination)


def write_json(payload: object, destination: Path) -> None:
    def strict_json(value: object) -> object:
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, dict):
            return {key: strict_json(item) for key, item in value.items()}
        if isinstance(value, list):
            return [strict_json(item) for item in value]
        if isinstance(value, tuple):
            return [strict_json(item) for item in value]
        return value

    destination.write_text(
        json.dumps(strict_json(payload), indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--paired-draws", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.draws < 100 or args.paired_draws < 100:
        raise RuntimeError("Bootstrap draw counts must be at least 100")

    repo = args.repo.resolve()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    items = frozen_items(repo)
    write_manifest(items, outdir / "benchmark_773_manifest.jsonl")
    write_mini_provenance(repo, outdir / "gpt54mini_27row_provenance.csv")
    write_csv(sequential_atom_map_rows(items), outdir / "b2_sequential_atom_maps.csv")
    write_csv(excluded_rows(repo / "benchmark/benchmark_v3_eval.jsonl"), outdir / "excluded_row_composition.csv")

    records: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []
    vectors_by_model: dict[str, dict[str, np.ndarray]] = {}
    input_paths: set[Path] = {repo / "benchmark/benchmark_v3_eval.jsonl"}
    provenance_path = (
        repo
        / "runs/benchmark_v3_gpt54mini_tools_no-sgr/gpt-5.4-mini/"
        "rescue_provenance.json"
    )
    input_paths.add(provenance_path)

    for model in RUNS:
        vectors, failure, paths = score_vectors(repo, model, items)
        vectors_by_model[model] = vectors
        failure_rows.append(failure)
        input_paths.update(paths)
        point = estimates(vectors)
        if abs(point["SuiteMacro"] * 100 - EXPECTED_SUITE_MACRO[model]) > 0.06:
            raise RuntimeError(
                f"SuiteMacro drift for {model}: {point['SuiteMacro'] * 100:.3f}%"
            )
        intervals = bootstrap(vectors, draws=args.draws, seed=args.seed)
        record: dict[str, object] = {"system_configuration": model, "model": model}
        for metric in METRICS:
            low, high = intervals[metric]
            record[metric] = round(point[metric] * 100, 3)
            record[f"{metric}_low"] = round(low * 100, 3)
            record[f"{metric}_high"] = round(high * 100, 3)
        records.append(record)

    write_json(records, outdir / "score_table_reproduced.json")
    write_csv(records, outdir / "score_table_reproduced.csv")
    # Backward-compatible filenames used by the document and figure builders.
    write_json(records, outdir / "table1_reproduced.json")
    write_csv(records, outdir / "table1_reproduced.csv")
    write_csv(failure_rows, outdir / "failure_taxonomy.csv")
    write_json(failure_rows, outdir / "failure_taxonomy.json")
    sensitivity = sensitivity_rows(repo, items)
    write_csv(sensitivity, outdir / "denominator_sensitivity.csv")
    write_json(sensitivity, outdir / "denominator_sensitivity.json")

    aggregation_rows: list[dict[str, object]] = []
    for metric in ("SuiteMacro", "Micro773", "SubtypeMacro6"):
        ordered = sorted(records, key=lambda row: float(row[metric]), reverse=True)
        for rank, row in enumerate(ordered, start=1):
            aggregation_rows.append(
                {
                    "aggregation": metric,
                    "rank": rank,
                    "system_configuration": row["system_configuration"],
                    "score_percent": row[metric],
                }
            )
    write_csv(aggregation_rows, outdir / "aggregation_sensitivity.csv")
    write_json(aggregation_rows, outdir / "aggregation_sensitivity.json")

    paired = paired_bootstrap(
        vectors_by_model["GPT-5.4"],
        vectors_by_model["GPT-5.4-mini"],
        draws=args.paired_draws,
        seed=args.seed,
    )
    write_csv([paired], outdir / "paired_top_comparison.csv")
    write_json(paired, outdir / "paired_top_comparison.json")

    judge_rows, judge_paths = judge_item_statistics(
        repo, items, draws=args.draws, seed=args.seed
    )
    input_paths.update(judge_paths)
    write_csv(judge_rows, outdir / "judge_common_item_statistics.csv")
    write_json(judge_rows, outdir / "judge_common_item_statistics.json")
    stored_root = Path(__file__).resolve().parent / "stored_artifacts"
    rubric_rows = rubric_sensitivity(repo, stored_root, outdir)
    coverage_rows, method_rows = coverage_and_methods(repo, outdir)
    write_hashes(input_paths, repo, outdir / "input_sha256.csv")
    human_root = Path(__file__).resolve().parent / "human_validation"
    human_rows = human_annotation_summary(human_root)
    write_csv(human_rows, outdir / "human_annotation_summary.csv")
    write_json(human_rows, outdir / "human_annotation_summary.json")
    environment = environment_record(repo)
    write_json(environment, outdir / "environment.json")

    summary = {
        "frozen_rows": len(items),
        "task_counts": EXPECTED_TASK_COUNTS,
        "bootstrap_draws": args.draws,
        "paired_bootstrap_draws": args.paired_draws,
        "seed": args.seed,
        "score_table": records,
        "paired_top_comparison": paired,
        "judge_answer_set": "GPT-5.4 SGR (the only stored GPT-5.4 answer set with sufficient three-judge coverage across all six frozen task subtypes)",
        "rubric_sensitivity": rubric_rows,
        "secondary_judge_coverage": coverage_rows,
        "score_method_taxonomy_rows": len(method_rows),
        "sequential_atom_map_rows": 186,
        "excluded_rows": 217,
        "environment": environment,
    }
    write_json(summary, outdir / "reproduction_summary.json")
    generated_paths = {
        path for path in outdir.iterdir()
        if path.is_file() and path.name != "output_sha256.csv"
    }
    write_csv(
        [
            {"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in sorted(generated_paths)
        ],
        outdir / "output_sha256.csv",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
