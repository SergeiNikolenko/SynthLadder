# SynthLadder

`SynthLadder` is a chemistry benchmark and evaluation package for language
models on reaction, immediate-precursor, and route-proposal tasks.

## What The Benchmark Measures
`benchmark_v3` is organized into three suites:

- `Suite A`: reaction tasks
- `Suite B`: immediate-precursor tasks
- `Suite C`: route-proposal tasks

The suites differ in source data, prompts, answer contracts, scoring rubrics,
and item maxima. They are organizational groups, not a calibrated scale of
planning depth. The repository also includes auxiliary chemistry role and
condition tasks outside the six subtypes used in the paper analysis.

The benchmark covers:

- organic chemistry reasoning
- retrosynthesis and route planning
- deterministic and rubric-based LLM evaluation

## Third-party data boundary

The current tree excludes PMechDB-derived chemical payloads from benchmark,
candidate, and judge JSONL files. For those rows, it retains composite keys,
task metadata, execution status, score method, and numeric scores needed to
reproduce the published aggregate analysis. Users must obtain PMechDB from its
official distribution and run the documented builders to reconstruct complete
task rows. SynthLadder's MIT license does not relicense third-party data.

This change does not remove affected objects from older Git history. Maintainers
must follow [the release-history notice](docs/RELEASE_HISTORY_NOTICE.md) before
publishing a clean release.

## Repository Layout

- `benchmark/`
  - public benchmark artifacts, eval subsets, and manifests
- `synthladder/agents/`
  - OpenShell runtime, tool registry, and SGR reasoning layer
- `synthladder/evaluation/`
  - student stage, judge stage, and matrix runner
- `synthladder/guards/`
  - typed validation and retry helpers for student and judge calls
- `synthladder/build/`
  - reproducible benchmark construction utilities
- `external_sources/`
  - source manifests, download links, and rebuild instructions
- `docs/`
  - architecture, ladder semantics, judging, taxonomy, and runtime policy

The public repository intentionally excludes generated runs, scratch analysis,
and legacy parsing pipelines that are not part of the final benchmark release.

## Reproducing the reported audit

`reproducibility_files/reproduce_scores.py` reconstructs the paper tables from
stored outputs. It also computes rubric sensitivity from the retained strict
B-suite score table, audits secondary-judge coverage across 48 stored files,
and reports score-method counts, including structured fallbacks. It does not
call candidate, judge, planner, or annotation endpoints.

```bash
uv run --frozen python reproducibility_files/reproduce_scores.py \
  --repo . \
  --outdir reproducibility_files/generated
```

The strict-rubric table and its source-commit provenance are in
`reproducibility_files/stored_artifacts/`. See `DATA_LICENSES.md` for the
third-party data boundary.

## Public Benchmark Files

Primary runtime entrypoint:

- `benchmark/benchmark_v3_eval.jsonl`

Per-level public eval subsets:

- `benchmark/level_a_eval.jsonl`
- `benchmark/level_b_eval.jsonl`
- `benchmark/level_c_eval.jsonl`

Supporting manifests:

- `benchmark/levels_manifest.yaml`
- `benchmark/paper_eval_manifest.yaml`
- `benchmark/LEVELS.md`

Legacy compatibility/source layer retained for selected construction steps:

- `benchmark/benchmark_v1_0.jsonl`

## Installation

Requirements:

- Python `3.12+`
- `uv`
- Docker for OpenShell-backed runs
- an OpenAI-compatible endpoint or local proxy

Setup:

```bash
git clone https://github.com/SergeiNikolenko/SynthLadder.git
cd SynthLadder
uv sync
```

The package is importable as `synthladder`.

## CLI Entry Points

Installed package entry points:

- `synthladder-student`
- `synthladder-judge`
- `synthladder-matrix`
- `synthladder-materialize`
- `synthladder-build`
- `synthladder-build-levels`
- `synthladder-build-paper-eval`

Module entry points:

- `python -m synthladder.evaluation.student_validation`
- `python -m synthladder.evaluation.llm_judge`
- `python -m synthladder.evaluation.run_full_matrix`
- `python -m synthladder.evaluation.materialize_benchmark_v3_eval`

## Runtime Setup

Export your model endpoint and API key:

```bash
export API_BASE_URL="http://127.0.0.1:8317/v1"
export CLIPROXY_API_KEY="<your-api-key>"
```

Quick health check:

```bash
curl -sS \
  -H "Authorization: Bearer $CLIPROXY_API_KEY" \
  "$API_BASE_URL/models"
```

If you run OpenShell-backed evaluation, make sure Docker and the OpenShell
gateway are available.

## Reproducing Benchmark Execution

### 1. Materialize the runtime-facing benchmark file

```bash
uv run synthladder-materialize \
  --output benchmark/benchmark_v3_eval.jsonl
```

### 2. Run student inference

```bash
uv run synthladder-student \
  --benchmark-path benchmark/benchmark_v3_eval.jsonl \
  --output-path runs/repro/student_output.jsonl \
  --api-base-url "$API_BASE_URL" \
  --model-name "gpt-5.4-mini" \
  --api-key "$CLIPROXY_API_KEY" \
  --agent-sandbox openshell \
  --agent-backend openshell_worker \
  --agent-tools-profile tools \
  --student-guard-enabled true \
  --student-guard-mode on_failure \
  --student-guard-retries 2
```

### 3. Run the judge

```bash
uv run synthladder-judge \
  --input-path runs/repro/student_output.jsonl \
  --gold-path benchmark/benchmark_v3_eval.jsonl \
  --judge-model "gpt-5.4-mini" \
  --judge-model-url "$API_BASE_URL" \
  --judge-api-key "$CLIPROXY_API_KEY" \
  --judge-method g_eval \
  --judge-g-eval-fallback-structured true \
  --judge-structured-retries 2 \
  --output-path runs/repro/llm_judge_output.jsonl
```

### 4. Run the full matrix pipeline

```bash
uv run synthladder-matrix \
  --benchmark-path benchmark/benchmark_v3_eval.jsonl \
  --api-base-url "$API_BASE_URL" \
  --api-key "$CLIPROXY_API_KEY" \
  --models gpt-5.4-mini \
  --judge-model gpt-5.4-mini \
  --agent-sandbox openshell \
  --agent-backend openshell_worker \
  --agent-tools-profile tools \
  --student-guard-enabled true \
  --student-guard-mode on_failure \
  --student-guard-retries 2 \
  --judge-method g_eval \
  --judge-g-eval-fallback-structured true \
  --judge-structured-retries 2
```

Outputs are written into `runs/<run-id>/`.

## Rebuilding The Benchmark From Sources

The repository does not redistribute raw external datasets. To rebuild the
larger benchmark pools:

1. download the public sources listed in [external_sources/README.md](external_sources/README.md)
2. place them into the expected `external_sources/<group>/<source>/raw|extracted` layout
3. run:

```bash
uv run synthladder-build-levels
uv run synthladder-build-paper-eval
uv run synthladder-materialize \
  --output benchmark/benchmark_v3_eval.jsonl
```

Build modules expose argparse CLIs, support `--help`, and fail fast on missing
source files or benchmark pools.

Restricted/commercial sources are documented in `external_sources/blocked/` but
are not redistributed.

## Evaluation Notes

- The default integrity-oriented runtime is `OpenShell`.
- `local` sandbox mode is a development fallback, not the preferred evaluation mode.
- The student path includes a hidden SGR reasoning phase for supported runs.
- The judge combines deterministic scoring with rubric-based LLM evaluation.
- `score_method` in `llm_judge_output.jsonl` records whether a row was scored by:
  - `deterministic`
  - `g_eval`
  - `structured_fallback`
  - `llm_judge`

## Documentation Map

- [docs/architecture.md](docs/architecture.md) - runtime and package structure
- [docs/benchmark_ladder.md](docs/benchmark_ladder.md) - benchmark semantics
- [docs/benchmark_construction.md](docs/benchmark_construction.md) - source-to-benchmark construction
- [docs/benchmark_taxonomy.md](docs/benchmark_taxonomy.md) - taxonomy and reporting
- [docs/g_eval.md](docs/g_eval.md) - judge behavior
- [docs/tools/README.md](docs/tools/README.md) - operational commands
- [docs/security_runbook.md](docs/security_runbook.md) - runtime and sandbox policy
