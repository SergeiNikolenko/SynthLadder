# Selected Chemist-Annotation Subset

This file records the documented selection procedure for the 63
chemist-annotated GPT-5.4 no-SGR answers reported in the manuscript. The
retained set is complete-case and interface-filtered; it is not a random
human-validation sample. Judge disagreement determined presentation order, not
set membership.

## Objective

Select tasks that the graphical review interface could render and for which all
three stored judges scored the same GPT-5.4 no-SGR answer, then prioritize the
largest judge disagreements.

## Source Run

- Candidate configuration: `gpt-5.4`
- Run: `benchmark_v3_gpt54_tools_no-sgr`
- Candidate answers: `runs/benchmark_v3_gpt54_tools_no-sgr/gpt-5.4/student_output.jsonl`

## Judges Used

The same GPT-5.4 student answers were scored by:

- GPT judge: `judge_gpt54mini`
- Gemini judge: `judge_gemini31flashlite`
- Qwen judge: `judge_qwen36_35b_a3b`

Only tasks with valid `row_status == "ok"` scores from all three judges were
eligible.

## Interface Filters

Tasks were retained only if the stored review interface could display the
candidate and reference material:

- Excluded `G` suite tasks, because they are mostly text role-extraction tasks
  rather than visual structure-comparison tasks.
- Excluded `reaction_center_identification`, because manual atom-map/bond-edit
  checking was too slow and visually noisy for this review workflow.
- Required a renderable input structure or target structure.
- Required a renderable benchmark gold structure.
- Required a renderable GPT-5.4 student answer.

These filters exclude every A1a reaction-center row as well as all A2, B2, and
Suite C rows from the final selected set.

## Ranking

For each eligible task, judge scores were normalized as:

```text
normalized_score = final_score / max_score
```

The disagreement score was:

```text
judge_spread = max(GPT, Gemini, Qwen) - min(GPT, Gemini, Qwen)
```

Tasks were sorted by descending `judge_spread`. The retained artifact contains
all 63 rows identified as interface-supported and complete-case during the
review workflow:
41 A1b transformation-classification/product rows and 22 B1 precursor rows.

## Why the artifact contains 63 tasks

The review workflow targeted 100 tasks, but only 63 satisfied all constraints:

- same GPT-5.4 no-SGR student answer,
- valid GPT/Gemini/Qwen judge scores,
- interface-supported molecular structure display,
- no G-suite text-role extraction,
- no reaction-center atom-map review.

All 63 retained rows were annotated; sorting by judge spread changed only their
presentation order. The original graphical-interface implementation and an
executable renderability-selection program were not retained, so the release
does not independently reconstruct the interface-support decision from the raw
candidate pool. Two chemist annotators, Daniil D. Kholmanskikh (`daniil`)
and Mark Yu. Schneider (`mark`), produced separate label files. The interface
offered the six scores 0, 2, 4, 6, 8, and 10, plus optional confidence and note
fields. It displayed the task and reference material, candidate answer, and the
canonical judge identity, score, and comment, so annotation was unblinded. The
retained interface and study documentation contain no separate written scoring
rubric beyond this scale and displayed material.

## Files

- `human_validation_subset.csv`: selected keys, task metadata, and stored judge scores.
- `human_labels_daniil_63.jsonl`: Daniil D. Kholmanskikh label file.
- `human_labels_mark_63.jsonl`: Mark Yu. Schneider label file.
