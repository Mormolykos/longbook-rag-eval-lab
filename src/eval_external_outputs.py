from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


QUESTION_ID_RE = re.compile(r"\b(?:bq|q)\d{3}\b", re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-z0-9_']+")
UNCERTAINTY_RE = re.compile(
    r"\b(?:uncertain|unsure|unclear|unknown|not\s+sure|cannot\s+determine|can't\s+determine|"
    r"needs\s+review|may|might|probably|possibly|appears|seems)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "answer",
    "because",
    "before",
    "being",
    "chapter",
    "could",
    "does",
    "from",
    "gold",
    "have",
    "into",
    "only",
    "question",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "through",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def _load_questions(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row.setdefault("id", f"q{line_no:03d}")
            row.setdefault("evidence_terms", [])
            row.setdefault("gold_answer", "")
            row.setdefault("expected_chapter", "")
            rows.append(row)
    return rows


def _normalize_for_phrase(text: str) -> str:
    return " ".join(WORD_RE.findall(str(text or "").lower()))


def _contains_phrase(text: str, phrase: str) -> bool:
    phrase_norm = _normalize_for_phrase(phrase)
    if not phrase_norm:
        return False
    return phrase_norm in _normalize_for_phrase(text)


def _gold_terms(gold_answer: str) -> List[str]:
    terms: List[str] = []
    for token in WORD_RE.findall(str(gold_answer or "").lower()):
        token = token.strip("'")
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token not in terms:
            terms.append(token)
    return terms


def _answer_has_content(answer: str) -> bool:
    tokens = WORD_RE.findall(str(answer or ""))
    return len(tokens) >= 3


def _line_qid(line: str, next_line: str = "") -> Optional[str]:
    stripped = line.strip()
    stripped = re.sub(r"^\s*#{1,6}\s*", "", stripped).strip()
    stripped = re.sub(r"^\s*[-*+]\s+", "", stripped).strip()
    stripped = stripped.replace("**", "").replace("__", "").replace("`", "").strip()

    direct_patterns = [
        r"^(?:qid|question)\s*[:#\-]?\s*((?:bq|q)\d{3})\b",
        r"^((?:bq|q)\d{3})\s*[:.\-]?\b",
    ]
    for pattern in direct_patterns:
        match = re.search(pattern, stripped, flags=re.IGNORECASE)
        if match:
            return match.group(1).lower()

    if re.fullmatch(r"qid\s*:?", stripped, flags=re.IGNORECASE):
        next_match = QUESTION_ID_RE.search(next_line)
        if next_match:
            return next_match.group(0).lower()

    return None


def _qid_segments(text: str) -> Dict[str, Tuple[int, int]]:
    lines = text.splitlines(keepends=True)
    starts: List[int] = []
    pos = 0
    for line in lines:
        starts.append(pos)
        pos += len(line)

    markers: List[Tuple[str, int, int]] = []
    for idx, line in enumerate(lines):
        next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
        qid = _line_qid(line, next_line=next_line)
        if not qid:
            continue
        markers.append((qid, starts[idx], starts[idx] + len(line)))

    markers.sort(key=lambda item: item[1])
    segments: Dict[str, Tuple[int, int]] = {}
    for idx, (qid, start, answer_start) in enumerate(markers):
        end = markers[idx + 1][1] if idx + 1 < len(markers) else len(text)
        segments.setdefault(qid, (answer_start, end))
    return segments


def _fallback_segment(text: str, qid: str) -> Optional[Tuple[int, int]]:
    match = re.search(rf"\b{re.escape(qid)}\b", text, flags=re.IGNORECASE)
    if not match:
        return None

    next_match = QUESTION_ID_RE.search(text, pos=match.end())
    end = next_match.start() if next_match else min(len(text), match.end() + 5000)
    return match.end(), end


def _extract_answer(text: str, qid: str, segments: Dict[str, Tuple[int, int]]) -> Tuple[bool, str]:
    qid_l = qid.lower()
    segment = segments.get(qid_l)
    if segment is None:
        segment = _fallback_segment(text, qid_l)
    if segment is None:
        return False, ""

    start, end = segment
    answer = text[start:end].strip()
    return _answer_has_content(answer), answer


def _score_question(
    system_name: str,
    text: str,
    question: Dict[str, object],
    segments: Dict[str, Tuple[int, int]],
    fallback_full_document: bool = False,
) -> Dict[str, object]:
    qid = str(question.get("id") or "").lower()
    qid_found = bool(re.search(rf"\b{re.escape(qid)}\b", text, flags=re.IGNORECASE))

    if fallback_full_document:
        answer_found_value: object = "fallback_full_document"
        answer = text
        qid_found = False
    else:
        answer_found, answer = _extract_answer(text, qid, segments)
        answer_found_value = int(answer_found)

    evidence_terms = question.get("evidence_terms") or []
    if not isinstance(evidence_terms, list):
        evidence_terms = []

    matched_evidence = [str(term) for term in evidence_terms if _contains_phrase(answer, str(term))]
    missing_evidence = [str(term) for term in evidence_terms if str(term) not in matched_evidence]
    evidence_coverage = (len(matched_evidence) / float(len(evidence_terms))) if evidence_terms else 0.0

    gold_terms = _gold_terms(str(question.get("gold_answer") or ""))
    matched_gold = [term for term in gold_terms if _contains_phrase(answer, term)]
    gold_coverage = (len(matched_gold) / float(len(gold_terms))) if gold_terms else 0.0

    notes: List[str] = []
    if not qid_found:
        notes.append("qid_missing")
    if fallback_full_document:
        notes.append("fallback_full_document_scoring")
    if qid_found and not answer_found_value:
        notes.append("answer_missing_after_qid")
    if UNCERTAINTY_RE.search(answer):
        notes.append("uncertainty_mention")

    return {
        "system_name": system_name,
        "question_id": qid,
        "qid_found": int(qid_found),
        "answer_found": answer_found_value,
        "gold_answer_coverage": round(float(gold_coverage), 6),
        "evidence_coverage": round(float(evidence_coverage), 6),
        "matched_evidence_terms": "; ".join(matched_evidence),
        "missing_evidence_terms": "; ".join(missing_evidence),
        "expected_chapter": str(question.get("expected_chapter") or ""),
        "notes": "; ".join(notes),
    }


def _answer_found_for_summary(value: object) -> int:
    if isinstance(value, str):
        return 1 if value.strip() == "fallback_full_document" else int(value.strip() or "0")
    return int(value)


def _system_name(path: Path) -> str:
    name = path.stem
    return re.sub(r"_?output$", "", name, flags=re.IGNORECASE)


def evaluate_systems(systems_dir: Path, questions_path: Path) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    questions = _load_questions(questions_path)
    rows: List[Dict[str, object]] = []
    system_summaries: List[Dict[str, object]] = []

    for md_path in sorted(Path(systems_dir).glob("*.md")):
        system_name = _system_name(md_path)
        text = _read_text(md_path)
        segments = _qid_segments(text)
        fallback_full_document = not bool(segments or QUESTION_ID_RE.search(text))
        system_rows = [
            _score_question(
                system_name,
                text,
                question,
                segments,
                fallback_full_document=fallback_full_document,
            )
            for question in questions
        ]
        rows.extend(system_rows)

        total = len(system_rows)
        qids_found = sum(int(row["qid_found"]) for row in system_rows)
        answers_found = sum(_answer_found_for_summary(row["answer_found"]) for row in system_rows)
        avg_gold = sum(float(row["gold_answer_coverage"]) for row in system_rows) / float(total or 1)
        avg_evidence = sum(float(row["evidence_coverage"]) for row in system_rows) / float(total or 1)
        zero_evidence = sum(1 for row in system_rows if float(row["evidence_coverage"]) <= 0.0)

        system_summaries.append(
            {
                "system_name": system_name,
                "total_questions": total,
                "qids_found": qids_found,
                "answers_found": answers_found,
                "avg_gold_answer_coverage": round(avg_gold, 6),
                "avg_evidence_coverage": round(avg_evidence, 6),
                "zero_evidence_questions": zero_evidence,
            }
        )

    ranked_by_evidence = sorted(
        system_summaries,
        key=lambda row: (-float(row["avg_evidence_coverage"]), str(row["system_name"])),
    )
    ranked_by_gold = sorted(
        system_summaries,
        key=lambda row: (-float(row["avg_gold_answer_coverage"]), str(row["system_name"])),
    )

    summary = {
        "systems": system_summaries,
        "ranked_by_evidence_coverage": [
            {
                "system_name": row["system_name"],
                "avg_evidence_coverage": row["avg_evidence_coverage"],
            }
            for row in ranked_by_evidence
        ],
        "ranked_by_gold_answer_coverage": [
            {
                "system_name": row["system_name"],
                "avg_gold_answer_coverage": row["avg_gold_answer_coverage"],
            }
            for row in ranked_by_gold
        ],
    }
    return rows, summary


def write_outputs(rows: List[Dict[str, object]], summary: Dict[str, object], csv_path: Path, summary_path: Path) -> None:
    csv_path = Path(csv_path)
    summary_path = Path(summary_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "system_name",
        "question_id",
        "qid_found",
        "answer_found",
        "gold_answer_coverage",
        "evidence_coverage",
        "matched_evidence_terms",
        "missing_evidence_terms",
        "expected_chapter",
        "notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    root = _project_root()
    parser = argparse.ArgumentParser(description="Evaluate external Markdown model outputs against gold questions.")
    parser.add_argument("--systems-dir", default=str(root / "data" / "systems"))
    parser.add_argument("--questions", default=str(root / "data" / "questions" / "questions.jsonl"))
    parser.add_argument("--csv-out", default=str(root / "reports" / "external_model_scores.csv"))
    parser.add_argument("--summary-out", default=str(root / "reports" / "external_model_summary.json"))
    args = parser.parse_args()

    rows, summary = evaluate_systems(Path(args.systems_dir), Path(args.questions))
    write_outputs(rows, summary, Path(args.csv_out), Path(args.summary_out))
    print(json.dumps({"rows": len(rows), "csv_out": args.csv_out, "summary_out": args.summary_out}, indent=2))


if __name__ == "__main__":
    main()
