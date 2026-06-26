# Results

## Experiment A Retrieval

| Method | Context precision | Context recall | Answer score | Latency seconds | Estimated tokens |
|---|---:|---:|---:|---:|---:|
| `naive_first_context` | 0.2600 | 0.2100 | 0.1979 | 0.000258 | 5282.9 |
| `naive_last_context` | 0.3700 | 0.3133 | 0.2071 | 0.000329 | 5841.5 |
| `flat_chunk_rag` | 0.5350 | 0.5617 | 0.2371 | 0.000639 | 5767.3 |
| `chapter_summary_chain` | 0.5600 | 0.5929 | 0.2313 | 0.043140 | 5938.9 |
| `hierarchical_book_rag` | 0.5600 | 0.5450 | 0.2283 | 0.043803 | 5986.8 |

Experiment A strongest retrieval method by context recall was `chapter_summary_chain` at 0.5929.

## Experiment A Free-Tier Consumer Model Outputs

| System | Questions | QIDs found | Answers found | Evidence-term coverage | Answer-term coverage | Zero-evidence questions |
|---|---:|---:|---:|---:|---:|---:|
| `chatgpt` | 40 | 40 | 40 | 0.5171 | 1.0000 | 3 |
| `copilot` | 40 | 40 | 40 | 0.8037 | 0.8010 | 0 |
| `gemini` | 40 | 40 | 40 | 0.9108 | 0.7930 | 0 |
| `grok` | 40 | 40 | 40 | 0.4963 | 1.0000 | 5 |
| `sonnet` | 40 | 40 | 40 | 0.7562 | 0.7916 | 0 |

Evidence-term coverage ranking: `gemini` (0.9108), `copilot` (0.8037), `sonnet` (0.7562), `chatgpt` (0.5171), `grok` (0.4963).

Answer-term coverage ranking: `chatgpt` (1.0000), `grok` (1.0000), `copilot` (0.8010), `gemini` (0.7930), `sonnet` (0.7916).

## Experiment B Retrieval

| Method | Context precision | Context recall | Answer score | Latency seconds | Estimated tokens |
|---|---:|---:|---:|---:|---:|
| `naive_first_context` | 0.1475 | 0.1458 | 0.2521 | 0.000823 | 5327.1 |
| `naive_last_context` | 0.4150 | 0.3302 | 0.3042 | 0.000838 | 6401.7 |
| `flat_chunk_rag` | 0.3375 | 0.4302 | 0.2833 | 0.001118 | 5529.6 |
| `chapter_summary_chain` | 0.4000 | 0.4771 | 0.2677 | 0.149321 | 5922.4 |
| `hierarchical_book_rag` | 0.3475 | 0.3365 | 0.2625 | 0.148537 | 6026.6 |

Experiment B strongest retrieval method by context recall was `chapter_summary_chain` at 0.4771. `naive_first_context` reached only 0.1458, a gap of 0.3312 and a ratio of 3.27x between `chapter_summary_chain` and `naive_first_context`.

## Experiment B Enhanced-Access Reference Runs

| System | Questions | QIDs found | Answers found | Evidence-term coverage | Answer-term coverage | Zero-evidence questions |
|---|---:|---:|---:|---:|---:|---:|
| `chatgpt_plus_gpt55_thinking` | 80 | 80 | 80 | 0.7354 | 0.9062 | 1 |
| `claude_code_opus48_high_thinking` | 80 | 80 | 80 | 0.9177 | 0.9415 | 0 |
| `claude_code_sonnet46_high_thinking` | 80 | 80 | 80 | 0.8698 | 0.8929 | 0 |
| `claude_code_sonnet46_low` | 80 | 80 | 80 | 0.7281 | 0.8556 | 4 |

Enhanced-access evidence-term coverage ranking: `claude_code_opus48_high_thinking` (0.9177), `claude_code_sonnet46_high_thinking` (0.8698), `chatgpt_plus_gpt55_thinking` (0.7354), `claude_code_sonnet46_low` (0.7281).

Enhanced-access answer-term coverage ranking: `claude_code_opus48_high_thinking` (0.9415), `chatgpt_plus_gpt55_thinking` (0.9062), `claude_code_sonnet46_high_thinking` (0.8929), `claude_code_sonnet46_low` (0.8556).

Enhanced Claude Opus 4.8 High Thinking ranked highest among enhanced-access rows by both evidence-term coverage (0.9177) and answer-term coverage (0.9415). ChatGPT Plus / GPT-5.5 Thinking is present as an enhanced-access reference row with evidence-term coverage 0.7354 and answer-term coverage 0.9062.

## Interpretation

Evidence coverage and gold-answer coverage can diverge, so short-answer correctness and evidence grounding should be reported separately. Experiment A shows this directly: Gemini ranked highest by evidence-term coverage, while ChatGPT and Grok tied at the top by answer-term coverage. Experiment B shows retrieval degradation under the longer corpus, especially for `naive_first_context`, and supports chapter-aware retrieval as a stronger baseline for this corpus.
