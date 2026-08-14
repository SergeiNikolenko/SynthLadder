# Gemini 3.1 Pro Preview Minimal No-SGR Result

Generated from primary judge output. Repair-adjusted score is not reported here; primary score uses the primary judge output.

| Run | Student rows | Judge rows | Quality score | End-to-end score | Reliability | Student errors | Empty answers | Repair status | Student tokens | Judge tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| `benchmark_v3_gemini31pro_minimal_no-sgr` | 990 | 990 | 61.91% | 59.74% | 95.96% | 40 | 40 | 40 repaired / 40 failed, 0 pending, 0 exhausted | 5,881,262 | 4,076,119 |

## Paths

| Artifact | Path |
|---|---|
| Student output | `runs/benchmark_v3_gemini31pro_minimal_no-sgr/student_output.jsonl` |
| Student verbose output | `runs/benchmark_v3_gemini31pro_minimal_no-sgr/student_output_verbose.jsonl` |
| Primary judge output | `runs/benchmark_v3_gemini31pro_minimal_no-sgr/judge_gpt54mini/llm_judge_output.jsonl` |
| Metrics | `runs/benchmark_v3_gemini31pro_minimal_no-sgr/metrics.json` |
| Summary CSV | `runs/benchmark_v3_gemini31pro_minimal_no-sgr/summary.csv` |
| Repair merged output | `runs/benchmark_v3_gemini31pro_minimal_no-sgr/repair_failed/student_output_merged.jsonl` |
| Repair status | `runs/benchmark_v3_gemini31pro_minimal_no-sgr/repair_failed/repair_status.json` |

## Notes

- Primary run and primary judge are complete at 990 rows.
- Primary score includes original failed/empty rows; repair status is recorded separately.
- Exhausted repair keys: 0.
