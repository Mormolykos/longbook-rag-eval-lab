# Hierarchical Retrieval-Augmented Evaluation for Long Narrative Documents

## Experiment A / Pilot Benchmark

This report presents Experiment A from the BedVibe LongBook RAG Eval Lab. The goal is not to claim a universal model ranking or a new state-of-the-art retrieval model. The goal is to test a reproducible local workflow for evaluating long narrative question answering, evidence grounding, and retrieval support.

The pilot uses one approximately 64k-word long narrative manuscript, 40 gold questions, 5 retrieval methods, and 5 external consumer AI systems. The external model evaluation produced 200 model-question scored rows. The combined retrieval-vs-model comparison contains 10 rows.

## Motivation

Long narrative documents create evaluation problems that short-context QA tasks often hide. A correct answer may depend on a character introduced many chapters earlier, a delayed artifact payoff, a chronology detail, or a location-specific clue. A model can also produce an answer that contains the short gold phrase while omitting the evidence trail that supports it. For manuscript QA, those are different product failures.

This motivates a LongBook Verifier / manuscript QA evaluator: a tool where a user can upload a book and a model output, then score evidence grounding, missing facts, chapter coverage, and answer support.

## Data

The gold dataset contains 40 questions derived from the local chapter map. The question set covers character identity, chronology, cause/effect, location, object/artifact, cross-chapter dependency, ending/payoff, and hidden clue or foreshadowing categories.

The chapter map identifies nine detected chapters/sections and records major characters, events, objects, artifacts, and locations. This map was used to create answerable gold questions with explicit evidence terms and expected chapter labels.

## Retrieval Methods

The retrieval comparison includes five methods:

- `naive_first_context`
- `naive_last_context`
- `flat_chunk_rag`
- `chapter_summary_chain`
- `hierarchical_book_rag`

The pilot retrieval results were:

| method | avg_context_precision | avg_context_recall | avg_answer_score | avg_latency | avg_tokens |
|---|---:|---:|---:|---:|---:|
| naive_first_context | 0.260 | 0.210 | 0.198 | 0.000 | 5282.850 |
| naive_last_context | 0.370 | 0.313 | 0.207 | 0.000 | 5841.475 |
| flat_chunk_rag | 0.535 | 0.562 | 0.237 | 0.001 | 5767.300 |
| chapter_summary_chain | 0.560 | 0.593 | 0.231 | 0.043 | 5938.850 |
| hierarchical_book_rag | 0.560 | 0.545 | 0.228 | 0.044 | 5986.775 |

`chapter_summary_chain` achieved the highest context recall-like score at 0.593. It outperformed the naive first-context baseline (0.210) and naive last-context baseline (0.313), supporting the idea that chapter-aware routing can improve evidence retrieval on long narrative text.

## External Model-Output Evaluation

The external output evaluation included five consumer AI systems and scored each output against the same 40 gold questions. The scoring is local/offline and uses transparent term overlap for evidence coverage and gold-answer coverage.

| system | QIDs found | answers found | avg_evidence_coverage | avg_gold_answer_coverage | zero_evidence_questions |
|---|---:|---:|---:|---:|---:|
| chatgpt | 40/40 | 40/40 | 0.517 | 1.000 | 3 |
| copilot | 40/40 | 40/40 | 0.804 | 0.801 | 0 |
| gemini | 40/40 | 40/40 | 0.911 | 0.793 | 0 |
| grok | 40/40 | 40/40 | 0.496 | 1.000 | 5 |
| sonnet | 40/40 | 40/40 | 0.756 | 0.792 | 0 |

Gemini ranked highest by evidence coverage at 0.911. ChatGPT and Grok ranked highest by gold-answer term coverage at 1.000.

## Evidence Coverage vs Answer-Term Coverage

The key pilot finding is that evidence coverage and answer-term coverage diverged. Gemini showed the highest evidence-term coverage but did not top gold-answer coverage. ChatGPT and Grok reached the highest gold-answer term coverage while showing lower evidence coverage. This suggests that answer-only grading can obscure whether a model actually grounded its answer in the manuscript evidence expected by the benchmark.

## Product Implication

A LongBook Verifier can make this distinction operational. The user-facing workflow is straightforward:

1. Upload a book.
2. Upload or paste model answers.
3. Score answer support against gold questions or generated QA probes.
4. Show missing evidence terms, chapter coverage, and answer-support metrics.
5. Compare retrieval methods and external systems without requiring remote model calls.

## Limitations

This is an Experiment A pilot, not a final benchmark. It uses one book only, and the questions were generated from a local chapter map. Term-overlap scoring is lightweight and does not replace semantic judgment. External model conditions may vary by free-tier interface and document-access behavior. Future work should expand to a multi-book and/or public-domain benchmark.

## Next Step

Experiment B should evaluate a four-book combined corpus around 200k words with 60 to 80 harder cross-book questions. The same retrieval methods and external output scoring pipeline should be used to compare single-book vs multi-book degradation.
