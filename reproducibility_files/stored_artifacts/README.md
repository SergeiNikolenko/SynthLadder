# Stored analysis artifacts

`gpt54_b_strict_rubric_scores.csv` contains row-level numeric scores for the
strict B-suite rubric used in the manuscript sensitivity analysis. It was
derived from the stored GPT-5.4 judge output at source commit
`3cab5d6d76e7e36907c037f29b4813451fef1eb0`; no candidate or judge endpoint was
called. The table contains only B1/B2 composite keys, task subtype, score,
maximum score, and score method. `gpt54_b_strict_rubric_provenance.json` records
the source commit, path, and original blob hash.

`secondary_judge_coverage_inputs.csv` records the 48 judge files used for the
16-configuration coverage audit, with hashes, row counts, usable frozen-score
counts, and coverage bands. `secondary_judge_coverage_summary.csv` is derived
from that manifest.

`score_method_taxonomy.csv` reports score-method counts for the seven canonical
no-SGR analyses and the three-judge GPT-5.4 SGR comparison set.
