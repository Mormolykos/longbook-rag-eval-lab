from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List


QID_LIKE_RE = re.compile(r"\bq\d{3}\b", re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-z0-9_']+")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def _safe_preview(text: str, limit: int = 500) -> str:
    preview = str(text or "")[:limit]
    preview = preview.replace("\x00", "")
    return preview.replace("\r\n", "\n").replace("\r", "\n")


def _load_questions(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row.setdefault("id", f"q{line_no:03d}")
            rows.append(row)
    return rows


def _load_scores(path: Path) -> List[Dict[str, str]]:
    if not Path(path).exists():
        return []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_summary(path: Path) -> Dict[str, object]:
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _system_name(path: Path) -> str:
    return re.sub(r"_?output$", "", path.stem, flags=re.IGNORECASE)


def _summary_by_system(summary: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    systems = summary.get("systems", [])
    if not isinstance(systems, list):
        return {}
    out: Dict[str, Dict[str, object]] = {}
    for row in systems:
        if isinstance(row, dict) and row.get("system_name"):
            out[str(row["system_name"])] = row
    return out


def _score_counts_by_system(scores: List[Dict[str, str]]) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {}
    for row in scores:
        system = str(row.get("system_name") or "")
        if not system:
            continue
        counts.setdefault(system, {"rows": 0, "qid_found_rows": 0, "answer_found_rows": 0})
        counts[system]["rows"] += 1
        if str(row.get("qid_found") or "").strip() in {"1", "true", "True"}:
            counts[system]["qid_found_rows"] += 1
        if str(row.get("answer_found") or "").strip() not in {"", "0", "false", "False"}:
            counts[system]["answer_found_rows"] += 1
    return counts


def audit_outputs(
    systems_dir: Path,
    questions_path: Path,
    scores_csv: Path,
    summary_json: Path,
) -> Dict[str, object]:
    questions = _load_questions(questions_path)
    scores = _load_scores(scores_csv)
    summary = _load_summary(summary_json)
    summary_lookup = _summary_by_system(summary)
    score_counts = _score_counts_by_system(scores)

    system_reports: List[Dict[str, object]] = []
    for md_path in sorted(Path(systems_dir).glob("*.md")):
        text = _read_text(md_path)
        qid_matches = [match.group(0).lower() for match in QID_LIKE_RE.finditer(text)]
        unique_qids = sorted(set(qid_matches))
        system = _system_name(md_path)

        system_reports.append(
            {
                "system_name": system,
                "file_name": md_path.name,
                "character_count": len(text),
                "approximate_word_count": len(WORD_RE.findall(text)),
                "q001_q002_q003_style_ids_present": bool(qid_matches),
                "detected_qid_count": len(qid_matches),
                "unique_detected_qid_count": len(unique_qids),
                "first_20_detected_qid_like_strings": qid_matches[:20],
                "contains_QID": bool(re.search(r"\bQID\b", text, flags=re.IGNORECASE)),
                "contains_Answer_colon": bool(re.search(r"\bAnswer\s*:", text, flags=re.IGNORECASE)),
                "contains_Evidence": bool(re.search(r"\bEvidence\b", text, flags=re.IGNORECASE)),
                "contains_Chapter": bool(re.search(r"\bChapter\b", text, flags=re.IGNORECASE)),
                "preview_first_500_characters": _safe_preview(text),
                "existing_score_rows": score_counts.get(system, {}),
                "existing_summary_metrics": summary_lookup.get(system, {}),
            }
        )

    return {
        "questions_count": len(questions),
        "systems_count": len(system_reports),
        "scores_csv": str(scores_csv),
        "summary_json": str(summary_json),
        "systems": system_reports,
    }


def write_json_report(report: Dict[str, object], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(report: Dict[str, object], path: Path) -> None:
    lines: List[str] = [
        "# External Model Output Audit",
        "",
        f"- Questions loaded: {report.get('questions_count', 0)}",
        f"- Systems audited: {report.get('systems_count', 0)}",
        f"- Scores CSV: `{report.get('scores_csv', '')}`",
        f"- Summary JSON: `{report.get('summary_json', '')}`",
        "",
    ]

    systems = report.get("systems", [])
    if not isinstance(systems, list):
        systems = []

    for row in systems:
        if not isinstance(row, dict):
            continue
        lines.extend(
            [
                f"## {row.get('system_name', '')}",
                "",
                f"- File name: `{row.get('file_name', '')}`",
                f"- Character count: {row.get('character_count', 0)}",
                f"- Approximate word count: {row.get('approximate_word_count', 0)}",
                f"- q001/q002/q003 style IDs present: {row.get('q001_q002_q003_style_ids_present', False)}",
                f"- Detected QID count: {row.get('detected_qid_count', 0)}",
                f"- Unique detected QID count: {row.get('unique_detected_qid_count', 0)}",
                f"- First 20 detected QID-like strings: {', '.join(row.get('first_20_detected_qid_like_strings', []))}",
                f"- Contains `QID`: {row.get('contains_QID', False)}",
                f"- Contains `Answer:`: {row.get('contains_Answer_colon', False)}",
                f"- Contains `Evidence`: {row.get('contains_Evidence', False)}",
                f"- Contains `Chapter`: {row.get('contains_Chapter', False)}",
                f"- Existing score rows: `{json.dumps(row.get('existing_score_rows', {}), ensure_ascii=False)}`",
                f"- Existing summary metrics: `{json.dumps(row.get('existing_summary_metrics', {}), ensure_ascii=False)}`",
                "",
                "Preview:",
                "",
            ]
        )
        preview = str(row.get("preview_first_500_characters") or "")
        lines.extend([f"    {line}" for line in preview.splitlines()])
        lines.append("")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    root = _project_root()
    parser = argparse.ArgumentParser(description="Audit external Markdown output formats before scoring.")
    parser.add_argument("--systems-dir", default=str(root / "data" / "systems"))
    parser.add_argument("--questions", default=str(root / "data" / "questions" / "questions.jsonl"))
    parser.add_argument("--scores-csv", default=str(root / "reports" / "external_model_scores.csv"))
    parser.add_argument("--summary-json", default=str(root / "reports" / "external_model_summary.json"))
    parser.add_argument("--json-out", default=str(root / "reports" / "external_output_audit.json"))
    parser.add_argument("--md-out", default=str(root / "reports" / "external_output_audit.md"))
    args = parser.parse_args()

    report = audit_outputs(
        systems_dir=Path(args.systems_dir),
        questions_path=Path(args.questions),
        scores_csv=Path(args.scores_csv),
        summary_json=Path(args.summary_json),
    )
    write_json_report(report, Path(args.json_out))
    write_markdown_report(report, Path(args.md_out))
    print(json.dumps({"json_out": args.json_out, "md_out": args.md_out}, indent=2))


if __name__ == "__main__":
    main()
