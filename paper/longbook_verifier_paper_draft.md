# LongBook Verifier: Evidence-Grounded Long-Book Evaluation for Narrative Manuscripts

## Abstract

LongBook Verifier is an evidence-grounded long-book evaluation workflow for testing whether retrieval methods and AI model outputs are supported by long narrative manuscripts. This final package reports Experiment A, a pilot single-book benchmark on *The Drowned Reach*, and Experiment B, an extended 240k-word stress-test benchmark on the Mirelands 5-book corpus. Experiment A uses an approximately 64k-word single-book benchmark with 40 gold questions, 5 retrieval methods, and 5 external consumer AI systems under a free-tier consumer protocol. Experiment B uses a high-density long-form fantasy corpus of 240,767 words and approximately 320,220 tokens, with 80 gold questions, 5 retrieval methods, and enhanced-access reference protocol runs from Claude-family systems plus ChatGPT Plus / GPT-5.5 Thinking when present.

The benchmark reports evidence-term coverage, answer-term coverage, retrieval context recall, and task-completion behavior separately. This separation matters because short-answer correctness and evidence grounding can diverge. The results are not a universal model ranking or state of the art claim; they are a pilot plus stress-test package for manuscript QA and reproducible long-document evaluation.

## Introduction

Long-form narrative manuscripts create a specific evaluation problem: relevant evidence is distributed across chapters, timelines, objects, characters, and delayed payoffs. This package evaluates that setting with gold questions, evidence-term coverage, answer-term coverage, retrieval context recall, and task-completion behavior.

The work is framed as LongBook Verifier: upload a manuscript and an AI output, then score evidence grounding, missing facts, chapter coverage, and answer support. The benchmark uses a high-density long-form fantasy corpus and a compressed multi-threaded fantasy corpus stress test, while avoiding claims of universal ranking or state of the art performance.

## Methods

## Protocols

This package separates a free-tier consumer protocol from an enhanced-access reference protocol. The free-tier consumer protocol is used for Experiment A external systems and reports task-completion behavior, QID parsing, evidence-term coverage, and answer-term coverage from local Markdown outputs. The enhanced-access reference protocol is used for the Experiment B 5-book model-output runs and is not included in the free-tier ranking.

Enhanced Claude Code and ChatGPT Plus runs are not included in the free-tier ranking. A non-completion note exists at `data/systems_mirelands5/sonnet_claude_ai_free_failed_output.md`; it records that Claude.ai free-tier Sonnet 4.6 did not complete the 80-question evaluation under continuation/quota limits after three free-account attempts, and is not included in the answer-quality ranking.

## Experiment A: Pilot Single-Book Benchmark

Experiment A uses *The Drowned Reach*, an approximately 64k-word single-book benchmark with 40 gold questions, 5 retrieval methods, and 5 external consumer AI systems. The external-model score table contains 200 model-question rows. The combined comparison table contains 10 rows.

## Experiment B: Extended 240k-Word Stress-Test Benchmark

Experiment B uses the Mirelands 5-book corpus, a compressed multi-threaded fantasy corpus with 240,767 words and approximately 320,220 tokens. It contains 80 gold questions and compares 5 retrieval methods. The enhanced-access summary contains 4 model-output rows: `chatgpt_plus_gpt55_thinking`, `claude_code_opus48_high_thinking`, `claude_code_sonnet46_high_thinking`, `claude_code_sonnet46_low`.

## Metrics

Retrieval methods are scored with context precision-like and context recall-like metrics based on evidence-term overlap, plus answer score, latency, and estimated tokens. External model outputs are scored with evidence-term coverage, answer-term coverage, QID detection, answer detection, zero-evidence question counts, and task-completion behavior. Term-overlap scoring is a lightweight audit signal rather than full semantic correctness.

## Results

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

## Discussion

Both experiments identify `chapter_summary_chain` as the strongest measured retrieval method by context recall. In Experiment B, `naive_first_context` fell to 0.1458 context recall while `chapter_summary_chain` reached 0.4771, showing the cost of beginning-of-book truncation on a 240k-word stress test.

The enhanced-access reference rows show strong coverage but are methodologically separate from free-tier consumer outputs. Enhanced Claude Opus 4.8 High Thinking ranked highest among enhanced-access rows on both evidence-term coverage and answer-term coverage. These results should be treated as reference protocol measurements, not as a free-tier leaderboard.

## Limitations

- This is a pilot plus extended stress-test benchmark, not a universal model ranking and not a state of the art claim.
- Term-overlap scoring is lightweight and is not full semantic correctness.
- QID parsing and fallback parsing may vary by Markdown format.
- The private corpus limits public reproducibility unless a public-domain parallel corpus is added.
- Model interfaces, quotas, and file-access behavior differ across systems and may change over time.
- Free-tier consumer protocol and enhanced-access reference protocol results should not be merged into a single leaderboard.
- Enhanced Claude Code and ChatGPT Plus runs are not included in the free-tier ranking.
- A non-completion note exists at `data/systems_mirelands5/sonnet_claude_ai_free_failed_output.md`; it records that Claude.ai free-tier Sonnet 4.6 did not complete the 80-question evaluation under continuation/quota limits after three free-account attempts, and is not included in the answer-quality ranking.
