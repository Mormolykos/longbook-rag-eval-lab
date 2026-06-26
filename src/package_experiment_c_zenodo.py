from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Iterable, List


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "dist" / "LongBook_Verifier_Experiment_C_Hierarchical_Retrieval_Ablation.zip"

PAPER_FILES = [
    "paper/experiment_c_ablation_paper.md",
    "paper/experiment_c_ablation_paper.html",
    "paper/experiment_c_ablation_paper.pdf",
    "paper/experiment_c_abstract.md",
    "paper/experiment_c_portfolio_summary.md",
    "paper/experiment_c_zenodo_description.md",
    "paper/experiment_c_limitations.md",
    "paper/experiment_c_readme.md",
    "paper/experiment_c_citation.cff",
    "paper/experiment_c_zenodo_metadata.json",
    "paper/experiment_c_upload_checklist.md",
]

PLOT_FILES = [
    "plots/experiment_c_recall_by_method.png",
    "plots/experiment_c_precision_by_method.png",
    "plots/experiment_c_failure_types.png",
    "plots/experiment_c_pipeline_diagram.png",
    "plots/experiment_c_oracle_vs_real_retrieval.png",
]

REPORT_FILES = [
    "reports/mirelands5_comparison.csv",
    "reports/mirelands5_ablation_results.csv",
    "reports/mirelands5_ablation_summary.md",
    "reports/mirelands5_ablation_summary.json",
]

CODE_FILES = [
    "src/build_index.py",
    "src/chunk_book.py",
    "src/metrics.py",
    "src/retrieve.py",
    "src/run_eval.py",
    "src/run_ablation.py",
    "src/package_experiment_c_zenodo.py",
    "requirements.txt",
]

FORBIDDEN_MARKERS = [
    "data/books/",
    "Mirelands_5book_corpus",
    ".docx",
    "__pycache__",
    ".pyc",
    ".venv",
    "venv/",
    "env/",
]


def _existing(paths: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for rel in paths:
        path = ROOT / rel
        if path.exists():
            out.append(path)
    return out


def _arcname(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _is_forbidden(arcname: str) -> bool:
    lowered = arcname.lower()
    return any(marker.lower() in lowered for marker in FORBIDDEN_MARKERS)


def build_zip() -> dict:
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    files = _existing(PAPER_FILES + PLOT_FILES + REPORT_FILES + CODE_FILES)
    missing = [
        rel
        for rel in PAPER_FILES + PLOT_FILES + REPORT_FILES + CODE_FILES
        if not (ROOT / rel).exists()
    ]

    included = []
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            arcname = _arcname(path)
            if _is_forbidden(arcname):
                raise RuntimeError(f"Refusing to package forbidden file: {arcname}")
            zf.write(path, arcname)
            included.append(arcname)

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = zf.namelist()
        forbidden = [name for name in names if _is_forbidden(name)]
        if forbidden:
            raise RuntimeError(f"Forbidden files found inside ZIP: {forbidden}")

    return {
        "zip_path": str(ZIP_PATH),
        "included_files": included,
        "missing_optional_or_required_files": missing,
        "private_corpus_excluded": True,
        "forbidden_markers_checked": FORBIDDEN_MARKERS,
    }


def main() -> None:
    print(json.dumps(build_zip(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
