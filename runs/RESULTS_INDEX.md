# Canonical Result Matrix

Target scope: 8 student models x 2 modes (no-SGR and SGR). Each run should have one student output and three judge outputs: GPT, Gemini, and Qwen.

Canonical judge outputs live in per-run judge directories:
`judge_gpt54mini`, `judge_gemini31flashlite`, and `judge_qwen36_35b_a3b`.
`GPT judge` excludes `judge_gpt_oss`, old top-level judge outputs, and legacy `judge_gpt4o_mini` lanes.

| student model | mode | run path | student | GPT judge | Gemini judge | Qwen judge | missing |
|---|---|---|---:|---:|---:|---:|---|
| gpt-5.4 | no-SGR | `runs/benchmark_v3_gpt54_tools_no-sgr/gpt-5.4` | 990 | 990 | 990 | 990 | - |
| gpt-5.4 | SGR | `runs/benchmark_v3_gpt54_tools_sgr/gpt-5.4` | 990 | 990 | 990 | 990 | - |
| gpt-5.4-mini | no-SGR | `runs/benchmark_v3_gpt54mini_tools_no-sgr/gpt-5.4-mini` | 990 | 990 | 783 | 990 | Gemini judge 207 |
| gpt-5.4-mini | SGR | `runs/benchmark_v3_gpt54mini_tools_sgr/gpt-5.4-mini` | 990 | 990 | 0 | 990 | Gemini judge 990 |
| gemini-3-flash | no-SGR | `runs/benchmark_v3_gemini3flash_minimal_no-sgr` | 990 | 990 | 990 | 0 | Qwen judge 990 |
| gemini-3-flash | SGR | `runs/benchmark_v3_gemini3flash_minimal_sgr` | 990 | 990 | 990 | 0 | Qwen judge 990 |
| gemini-3.1-pro | no-SGR | `runs/benchmark_v3_gemini31pro_minimal_no-sgr` | 990 | 990 | 990 | 0 | Qwen judge 990 |
| gemini-3.1-pro | SGR | `runs/benchmark_v3_gemini31pro_minimal_sgr` | 444 | 444 | 238 | 0 | student 546; GPT judge 546; Gemini judge 752; Qwen judge 990 |
| gpt-oss | no-SGR | `runs/benchmark_v3_gptoss_tools_no-sgr` | 990 | 990 | 0 | 990 | Gemini judge 990 |
| gpt-oss | SGR | `runs/benchmark_v3_gptoss_tools_sgr` | 990 | 990 | 0 | 990 | Gemini judge 990 |
| qwen36_35b_a3b | no-SGR | `runs/benchmark_v3_qwen36_35b_a3b_minimal_no-sgr` | 990 | 990 | 0 | 428 | Gemini judge 990; Qwen judge 562 |
| qwen36_35b_a3b | SGR | `runs/benchmark_v3_qwen36_35b_a3b_minimal_sgr` | 990 | 990 | 0 | 0 | Gemini judge 990; Qwen judge 990 |
| glm-5.1 | no-SGR | `runs/benchmark_v3_glm51_minimal_no-sgr` | 990 | 990 | 990 | 0 | Qwen judge 990 |
| glm-5.1 | SGR | `runs/benchmark_v3_glm51_minimal_sgr` | 990 | 0 | 0 | 0 | GPT judge 990; Gemini judge 990; Qwen judge 990 |
| gemma4_31b | no-SGR | `runs/benchmark_v3_gemma4_31b_it_aitunnel_minimal_no-sgr` | 990 | 0 | 0 | 0 | GPT judge 990; Gemini judge 990; Qwen judge 990 |
| gemma4_31b | SGR | `runs/benchmark_v3_gemma4_31b_it_aitunnel_minimal_sgr` | 990 | 0 | 0 | 0 | GPT judge 990; Gemini judge 990; Qwen judge 990 |

Summary: 16 canonical runs. Complete student outputs: 15/16. Complete GPT judges: 12/16. Complete Gemini judges: 6/16. Complete Qwen judges: 6/16. Fully complete with all three judges: 2/16.
