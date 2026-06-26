from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List


COMBINED_COLUMNS = [
    "source_type",
    "name",
    "retrieval_avg_context_precision",
    "retrieval_avg_context_recall",
    "retrieval_avg_answer_score",
    "retrieval_avg_latency",
    "retrieval_avg_tokens",
    "model_avg_gold_answer_coverage",
    "model_avg_evidence_coverage",
    "model_qids_found",
    "model_answers_found",
    "model_total_questions",
    "model_zero_evidence_questions",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_retrieval_rows(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "source_type": "retrieval_method",
                    "name": row.get("method", ""),
                    "retrieval_avg_context_precision": row.get("avg_context_precision", ""),
                    "retrieval_avg_context_recall": row.get("avg_context_recall", ""),
                    "retrieval_avg_answer_score": row.get("avg_answer_score", ""),
                    "retrieval_avg_latency": row.get("avg_latency", ""),
                    "retrieval_avg_tokens": row.get("avg_tokens", ""),
                    "model_avg_gold_answer_coverage": "",
                    "model_avg_evidence_coverage": "",
                    "model_qids_found": "",
                    "model_answers_found": "",
                    "model_total_questions": "",
                    "model_zero_evidence_questions": "",
                }
            )
    return rows


def _read_model_rows(path: Path) -> List[Dict[str, object]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    systems = data.get("systems", [])
    if not isinstance(systems, list):
        systems = []

    rows: List[Dict[str, object]] = []
    for row in systems:
        rows.append(
            {
                "source_type": "external_model_output",
                "name": row.get("system_name", ""),
                "retrieval_avg_context_precision": "",
                "retrieval_avg_context_recall": "",
                "retrieval_avg_answer_score": "",
                "retrieval_avg_latency": "",
                "retrieval_avg_tokens": "",
                "model_avg_gold_answer_coverage": row.get("avg_gold_answer_coverage", ""),
                "model_avg_evidence_coverage": row.get("avg_evidence_coverage", ""),
                "model_qids_found": row.get("qids_found", ""),
                "model_answers_found": row.get("answers_found", ""),
                "model_total_questions": row.get("total_questions", ""),
                "model_zero_evidence_questions": row.get("zero_evidence_questions", ""),
            }
        )
    return rows


def write_combined(retrieval_csv: Path, model_summary_json: Path, out_csv: Path) -> List[Dict[str, object]]:
    rows = _read_retrieval_rows(retrieval_csv) + _read_model_rows(model_summary_json)
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMBINED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in COMBINED_COLUMNS})
    return rows


def main() -> None:
    root = _project_root()
    parser = argparse.ArgumentParser(description="Combine retrieval and external model-output comparison tables.")
    parser.add_argument("--retrieval-csv", default=str(root / "reports" / "drowned_comparison.csv"))
    parser.add_argument("--model-summary", default=str(root / "reports" / "external_model_summary.json"))
    parser.add_argument("--out", default=str(root / "reports" / "combined_retrieval_vs_models.csv"))
    args = parser.parse_args()

    rows = write_combined(Path(args.retrieval_csv), Path(args.model_summary), Path(args.out))
    print(json.dumps({"rows": len(rows), "out": args.out}, indent=2))


if __name__ == "__main__":
    main()
