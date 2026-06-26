# Experiment C Readme

Experiment C is a Zenodo-ready follow-up artifact for LongBook Verifier.

Title:

**Diagnosing Hierarchical Retrieval Failure in Long-Document RAG: A LongBook Verifier Ablation Study**

The experiment diagnoses why hierarchical book RAG underperformed chapter-summary chain in the Experiment B long-book benchmark.

## Inputs

Experiment C uses:

- the existing Experiment B 5-book corpus
- the existing 80 gold questions
- the existing LongBook Verifier scoring style

The public release package excludes full manuscript text and raw book files.

## Run

From the project root:

```powershell
python src\run_ablation.py
```

Expected outputs:

- `reports\mirelands5_ablation_results.csv`
- `reports\mirelands5_ablation_summary.md`
- `reports\mirelands5_ablation_summary.json`

## Package

Create the Zenodo upload ZIP:

```powershell
python src\package_experiment_c_zenodo.py
```

Expected output:

- `dist\LongBook_Verifier_Experiment_C_Hierarchical_Retrieval_Ablation.zip`

## Main Result

The current hierarchical method achieved context recall 0.3365. Removing neighbor expansion raised recall to 0.4771, matching chapter-summary chain. Oracle chapter routing raised recall to 0.7844. The result supports the error-compounding hypothesis but also identifies neighbor-expansion dilution as a major failure mode.
