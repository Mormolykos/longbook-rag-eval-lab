# Zenodo Description

## Title

Diagnosing Hierarchical Retrieval Failure in Long-Document RAG: A LongBook Verifier Ablation Study

## Abstract

This Zenodo artifact contains Experiment C, a follow-up ablation study for the LongBook Verifier benchmark. The study diagnoses why the original hierarchical book RAG method underperformed chapter-summary chain in a 5-book, 240,767-word long-form narrative corpus with 80 gold questions.

Experiment C compares five variants: current hierarchical retrieval, hierarchical retrieval without neighbor expansion, chapter-summary chain, oracle-chapter retrieval, and oracle-chapter retrieval with neighbor expansion. The current hierarchical method achieved context recall 0.3365 and precision 0.3475. Removing neighbor expansion raised recall to 0.4771 and precision to 0.4000, matching chapter-summary chain. Oracle chapter routing raised recall to 0.7844 and precision to 0.6796.

The results support the diagnosis that the original hierarchical method underperformed due to both first-stage chapter-selection limits and neighbor-expansion dilution. This is a corpus/protocol-specific diagnostic study, not a universal claim against hierarchical retrieval.

## Keywords

- long-document RAG
- retrieval-augmented generation
- hierarchical retrieval
- ablation study
- long-book evaluation
- evidence grounding
- narrative QA
- LongBook Verifier
- BookProof

## Related Identifier

Original LongBook Verifier research package: https://doi.org/10.5281/zenodo.20513116

## Author

Panagiotis Gkilis

## License Suggestion

Use CC-BY-4.0 for the paper, reports, figures, and metadata. Use MIT only for code files if a separate code license is desired.

## Included Materials

- Experiment C paper files
- ablation summary reports
- ablation result CSV
- figures
- `src/run_ablation.py`
- `src/package_experiment_c_zenodo.py`
- minimal reproducibility configuration

## Excluded Materials

The package intentionally excludes full manuscripts, raw book text, and private corpus files.
