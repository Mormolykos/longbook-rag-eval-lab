# Zenodo README

## Title

LongBook Verifier: Evidence-Grounded Long-Book Evaluation for Narrative Manuscripts

## Scope

This archive contains a pilot single-book benchmark and an extended 240k-word stress-test benchmark for evidence-grounded long-book evaluation. It is designed to support LongBook Verifier, a manuscript QA evaluator where users can upload a manuscript and AI output, then score evidence grounding, missing facts, chapter coverage, answer support, and task-completion behavior.

## Included Results

- Experiment A: *The Drowned Reach*, approximately 64k words, 40 gold questions, 5 retrieval methods, 5 external consumer AI systems.
- Experiment B: Mirelands 5-book corpus, 240,767 words, approximately 320,220 tokens, 80 gold questions, 5 retrieval methods.
- Enhanced-access reference protocol: Claude-family enhanced-access runs and ChatGPT Plus / GPT-5.5 Thinking if present in the enhanced summary.

## Protocol Separation

Free-tier consumer protocol results and enhanced-access reference protocol results are reported separately. Enhanced Claude Code and ChatGPT Plus runs are not included in the free-tier ranking.

## Reproducibility Note

If the private manuscript text cannot be redistributed, publish the code, schemas, aggregate metrics, plots, and a public-domain replication plan. Before archive release, independently audit the gold questions and evidence terms.
