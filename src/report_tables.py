from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path
from typing import Dict, Iterable, List


SUMMARY_FIELDS = [
    "method",
    "avg_context_precision",
    "avg_context_recall",
    "avg_answer_score",
    "avg_latency",
    "avg_tokens",
]


def _expand_run_args(values: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for value in values:
        matches = [Path(p) for p in glob.glob(value)]
        if matches:
            out.extend(matches)
        else:
            out.append(Path(value))
    return out


def _average(values: List[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0


def _summary_from_metrics(run_dir: Path) -> Dict[str, object]:
    metrics_path = run_dir / "metrics.csv"
    rows: List[Dict[str, str]] = []
    with metrics_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows.extend(reader)

    methods = [row.get("method") or run_dir.name for row in rows]
    method = methods[0] if methods else run_dir.name

    return {
        "method": method,
        "avg_context_precision": _average([float(row.get("context_precision_like") or 0.0) for row in rows]),
        "avg_context_recall": _average([float(row.get("context_recall_like") or 0.0) for row in rows]),
        "avg_answer_score": _average([float(row.get("answer_contains_gold_terms") or 0.0) for row in rows]),
        "avg_latency": _average([float(row.get("latency_seconds") or 0.0) for row in rows]),
        "avg_tokens": _average([float(row.get("tokens_estimated") or 0.0) for row in rows]),
    }


def load_run_summary(run_dir: Path) -> Dict[str, object]:
    run_dir = Path(run_dir)
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return {
            "method": data.get("method") or run_dir.name,
            "avg_context_precision": data.get("avg_context_precision", 0.0),
            "avg_context_recall": data.get("avg_context_recall", 0.0),
            "avg_answer_score": data.get("avg_answer_score", 0.0),
            "avg_latency": data.get("avg_latency", 0.0),
            "avg_tokens": data.get("avg_tokens", 0.0),
        }

    if (run_dir / "metrics.csv").exists():
        return _summary_from_metrics(run_dir)

    raise FileNotFoundError(f"No summary.json or metrics.csv found in {run_dir}")


def write_comparison(run_dirs: List[Path], out_path: Path) -> List[Dict[str, object]]:
    rows = [load_run_summary(path) for path in run_dirs]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in SUMMARY_FIELDS})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build comparison tables for long-book RAG runs.")
    parser.add_argument("--runs", nargs="+", required=True, help="Run folders or glob patterns.")
    parser.add_argument("--out", default="reports/comparison.csv", help="Output comparison CSV.")
    args = parser.parse_args()

    rows = write_comparison(_expand_run_args(args.runs), Path(args.out))
    print(json.dumps({"rows": len(rows), "out": args.out}, indent=2))


if __name__ == "__main__":
    main()
