# Frozen analysis reproduction

`reproduce_scores.py` reconstructs the manuscript tables from the retained,
redacted numeric artifacts. It performs no candidate-model, judge-model,
planner, or chemist-annotation inference.

From the repository root, run:

```text
uv run --frozen python reproducibility_files/reproduce_scores.py \
  --repo . --outdir reproducibility_files/generated
```

The generated `environment.json` records the source-artifact commit from which
the retained analysis inputs originated and identifies the current tree as the
payload-redacted publication release. The public release commit is specified in
the manuscript and release handoff because embedding that commit's own hash in
its tracked files would be self-referential.

The `generated/` directory contains the reproduced score tables, sensitivity
analyses, coverage and annotation summaries, input and output hashes, and the
recorded execution environment. The `stored_artifacts/` directory contains the
frozen strict-rubric and coverage inputs used by the measurement audit.
