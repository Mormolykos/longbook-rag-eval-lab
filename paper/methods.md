# Methods

## Protocols

This package separates a free-tier consumer protocol from an enhanced-access reference protocol. The free-tier consumer protocol is used for Experiment A external systems and reports task-completion behavior, QID parsing, evidence-term coverage, and answer-term coverage from local Markdown outputs. The enhanced-access reference protocol is used for the Experiment B 5-book model-output runs and is not included in the free-tier ranking.

Enhanced Claude Code and ChatGPT Plus runs are not included in the free-tier ranking. A non-completion note exists at `data/systems_mirelands5/sonnet_claude_ai_free_failed_output.md`; it records that Claude.ai free-tier Sonnet 4.6 did not complete the 80-question evaluation under continuation/quota limits after three free-account attempts, and is not included in the answer-quality ranking.

## Experiment A: Pilot Single-Book Benchmark

Experiment A uses *The Drowned Reach*, an approximately 64k-word single-book benchmark with 40 gold questions, 5 retrieval methods, and 5 external consumer AI systems. The external-model score table contains 200 model-question rows. The combined comparison table contains 10 rows.

## Experiment B: Extended 240k-Word Stress-Test Benchmark

Experiment B uses the Mirelands 5-book corpus, a compressed multi-threaded fantasy corpus with 240,767 words and approximately 320,220 tokens. It contains 80 gold questions and compares 5 retrieval methods. The enhanced-access summary contains 4 model-output rows: `chatgpt_plus_gpt55_thinking`, `claude_code_opus48_high_thinking`, `claude_code_sonnet46_high_thinking`, `claude_code_sonnet46_low`.

## Metrics

Retrieval methods are scored with context precision-like and context recall-like metrics based on evidence-term overlap, plus answer score, latency, and estimated tokens. External model outputs are scored with evidence-term coverage, answer-term coverage, QID detection, answer detection, zero-evidence question counts, and task-completion behavior. Term-overlap scoring is a lightweight audit signal rather than full semantic correctness.
