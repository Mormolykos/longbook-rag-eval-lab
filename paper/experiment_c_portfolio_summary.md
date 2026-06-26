# LongBook Verifier Experiment C — Hierarchical Retrieval Ablation

Diagnosed why hierarchical book RAG underperformed chapter-summary retrieval in the LongBook Verifier 5-book narrative benchmark.

Experiment C tested five retrieval variants across the existing 240,767-word corpus and 80 gold questions. The original hierarchical method achieved context recall 0.3365, while chapter-summary chain achieved 0.4771. Removing neighbor expansion raised hierarchical recall to 0.4771, matching chapter-summary chain. An oracle-chapter diagnostic run raised recall to 0.7844.

The study supports the error-compounding hypothesis but shows it was incomplete: wrong or weak first-stage chapter selection can damage downstream retrieval, and neighbor expansion caused major context dilution in 32 of 80 current-hierarchical cases. The result is a practical lesson for long-document RAG: multi-stage retrieval pipelines need stage-level ablation before their failures can be interpreted.

Suggested portfolio label:

**LongBook Verifier Experiment C — Hierarchical Retrieval Ablation**

Suggested portfolio paragraph:

Built a follow-up ablation study for LongBook Verifier to diagnose why hierarchical book RAG underperformed chapter-summary retrieval on a 240,767-word long narrative benchmark. The study compared current hierarchical retrieval, no-neighbor hierarchical retrieval, oracle-chapter retrieval, oracle-chapter retrieval with neighbors, and chapter-summary chain across 80 gold questions. It found that oracle chapter routing raised recall to 0.7844, while disabling neighbor expansion raised hierarchical recall from 0.3365 to 0.4771, matching chapter-summary chain. The result supported the error-compounding hypothesis but also identified neighbor dilution as a major failure mode.
