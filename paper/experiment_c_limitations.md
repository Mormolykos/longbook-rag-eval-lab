# Experiment C Limitations

Experiment C is a diagnostic ablation study, not a universal benchmark.

Limitations:

- The study uses a single private narrative corpus.
- The evaluation set contains 80 gold questions.
- The gold questions were written by the corpus author, not by independent benchmark annotators.
- The evidence-term scoring is lightweight and does not provide full semantic correctness judgment.
- No confidence intervals are reported because the current package did not compute them.
- The oracle chapter variants are diagnostic and not production-realistic because they use gold expected-chapter labels.
- The results do not establish a universal rule against hierarchical RAG.
- The public package excludes full manuscript text, which protects privacy but limits full public reproducibility unless a public-domain parallel corpus is added later.

The safe interpretation is that this corpus/protocol exposed two measurable failure modes in the tested hierarchical pipeline: first-stage chapter-selection limits and neighbor-expansion dilution.
