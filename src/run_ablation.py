from __future__ import annotations

import csv
import json
import re
import statistics
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from chunk_book import chunk_book_file, read_book_text
from metrics import context_precision_like, context_recall_like
from retrieve import embed_texts, retrieve_from_embeddings
from run_eval import (
    _build_chapter_records,
    _expand_neighbors,
    _rank_chapters,
    _retrieve_within_chapters,
    load_questions,
)


ROOT = Path(__file__).resolve().parents[1]
BOOK_PATH = ROOT / "data" / "books" / "Mirelands_5book_corpus.txt"
QUESTIONS_PATH = ROOT / "data" / "questions" / "mirelands_5book_questions.jsonl"
RESULTS_CSV = ROOT / "reports" / "mirelands5_ablation_results.csv"
SUMMARY_MD = ROOT / "reports" / "mirelands5_ablation_summary.md"
SUMMARY_JSON = ROOT / "reports" / "mirelands5_ablation_summary.json"

TOP_K = 5
CHUNK_SIZE_WORDS = 900
OVERLAP_WORDS = 120
EMBEDDING_BACKEND = "hashing_numpy"

BOOK_HEADING_RE = re.compile(r"(?im)^\s*#{1,6}\s*(BOOK\s+\d+:[^\n]+?)\s*$")
CHAPTER_HEADING_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?"
    r"(Chapter\s+(?:\d+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|"
    r"Eleven|Twelve|Thirteen)\b[^\n]{0,100})\s*$"
)
TERM_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class OracleSection:
    book_title: str
    chapter_title: str
    start_char: int
    end_char: int


def _clean_title(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _canon(value: object) -> str:
    text = str(value or "").lower()
    text = text.replace("\u2014", " ").replace("\u2013", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _norm_text(value: object) -> str:
    return " ".join(TERM_RE.findall(str(value or "").lower()))


def _contains_term(text: str, term: str) -> bool:
    norm_term = _norm_text(term)
    if not norm_term:
        return False
    return norm_term in _norm_text(text)


def _evidence_counts(contexts: List[Dict[str, object]], terms: Iterable[object]) -> Tuple[int, int]:
    term_list = [_clean_title(term) for term in terms if _clean_title(term)]
    context_text = " ".join(str(chunk.get("text") or "") for chunk in contexts)
    found = sum(1 for term in term_list if _contains_term(context_text, term))
    return found, len(term_list)


def _avg(values: Iterable[float]) -> float:
    vals = [float(value) for value in values]
    return float(statistics.fmean(vals)) if vals else 0.0


def _chapter_label(chapter: Dict[str, object]) -> str:
    return f"{chapter.get('chapter_id')}:{chapter.get('chapter_title')}"


def _selected_chunk_ids(contexts: List[Dict[str, object]]) -> str:
    return "|".join(str(chunk.get("id") or "") for chunk in contexts)


def _as_bool_int(value: bool) -> int:
    return 1 if value else 0


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def _chapter_ranges(chunks: List[Dict[str, object]]) -> Dict[str, Tuple[int, int]]:
    ranges: Dict[str, Tuple[int, int]] = {}
    for chunk in chunks:
        chapter_id = str(chunk.get("chapter_id") or "")
        start = int(chunk.get("start_char") or 0)
        end = int(chunk.get("end_char") or start)
        if chapter_id not in ranges:
            ranges[chapter_id] = (start, end)
        else:
            old_start, old_end = ranges[chapter_id]
            ranges[chapter_id] = (min(old_start, start), max(old_end, end))
    return ranges


def _attach_ranges(
    chapters: List[Dict[str, object]],
    chunks: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    ranges = _chapter_ranges(chunks)
    out: List[Dict[str, object]] = []
    for chapter in chapters:
        row = dict(chapter)
        start, end = ranges.get(str(chapter.get("chapter_id") or ""), (0, 0))
        row["start_char"] = start
        row["end_char"] = end
        out.append(row)
    return out


def _parse_oracle_sections(text: str) -> List[OracleSection]:
    book_matches = list(BOOK_HEADING_RE.finditer(text))
    sections: List[OracleSection] = []

    for idx, book_match in enumerate(book_matches):
        book_title = _clean_title(book_match.group(1))
        book_start = book_match.end()
        book_end = book_matches[idx + 1].start() if idx + 1 < len(book_matches) else len(text)
        chapter_matches = list(CHAPTER_HEADING_RE.finditer(text, book_start, book_end))

        for chapter_idx, chapter_match in enumerate(chapter_matches):
            chapter_title = _clean_title(chapter_match.group(1))
            section_start = chapter_match.start()
            section_end = (
                chapter_matches[chapter_idx + 1].start()
                if chapter_idx + 1 < len(chapter_matches)
                else book_end
            )
            sections.append(
                OracleSection(
                    book_title=book_title,
                    chapter_title=chapter_title,
                    start_char=section_start,
                    end_char=section_end,
                )
            )

    return sections


def _section_lookup(sections: List[OracleSection]) -> Dict[Tuple[str, str], OracleSection]:
    lookup: Dict[Tuple[str, str], OracleSection] = {}
    for section in sections:
        lookup[(_canon(section.book_title), _canon(section.chapter_title))] = section
    return lookup


def _expected_section(
    question: Dict[str, object],
    lookup: Dict[Tuple[str, str], OracleSection],
) -> Optional[OracleSection]:
    key = (_canon(question.get("expected_book")), _canon(question.get("expected_chapter")))
    return lookup.get(key)


def _chapter_matches_section(chapter: Dict[str, object], section: Optional[OracleSection]) -> bool:
    if section is None:
        return False
    if _canon(chapter.get("chapter_title")) != _canon(section.chapter_title):
        return False
    start = int(chapter.get("start_char") or 0)
    end = int(chapter.get("end_char") or start)
    return _overlaps(start, end, section.start_char, section.end_char)


def _hit_at(ranked: List[Dict[str, object]], section: Optional[OracleSection], k: int) -> bool:
    return any(_chapter_matches_section(chapter, section) for chapter in ranked[:k])


def _oracle_chunk_indices(
    chunks: List[Dict[str, object]],
    section: Optional[OracleSection],
) -> List[int]:
    if section is None:
        return []
    indices: List[int] = []
    for idx, chunk in enumerate(chunks):
        start = int(chunk.get("start_char") or 0)
        end = int(chunk.get("end_char") or start)
        if _overlaps(start, end, section.start_char, section.end_char):
            indices.append(idx)
    return indices


def _retrieve_from_indices(
    question: str,
    chunks: List[Dict[str, object]],
    embeddings: np.ndarray,
    metadata: Dict[str, object],
    indices: List[int],
    top_k: int,
) -> List[Dict[str, object]]:
    if not indices:
        return []
    candidate_chunks = [dict(chunks[idx]) for idx in indices]
    candidate_embeddings = np.asarray(embeddings[indices], dtype=np.float32)
    return retrieve_from_embeddings(
        query=question,
        chunks=candidate_chunks,
        embeddings=candidate_embeddings,
        metadata=metadata,
        top_k=top_k,
    )


def _base_row(
    question_item: Dict[str, object],
    method: str,
    ranked_top5: List[Dict[str, object]],
    section: Optional[OracleSection],
    contexts: List[Dict[str, object]],
    elapsed: float,
) -> Dict[str, object]:
    evidence_terms = question_item.get("evidence_terms") or []
    if not isinstance(evidence_terms, list):
        evidence_terms = []

    evidence_found, evidence_total = _evidence_counts(contexts, evidence_terms)
    hit1 = _hit_at(ranked_top5, section, 1)
    hit3 = _hit_at(ranked_top5, section, 3)
    hit5 = _hit_at(ranked_top5, section, 5)

    return {
        "question_id": str(question_item.get("id") or ""),
        "question": str(question_item.get("question") or ""),
        "expected_chapter": str(question_item.get("expected_chapter") or ""),
        "method": method,
        "predicted_chapter_top1": _chapter_label(ranked_top5[0]) if ranked_top5 else "",
        "predicted_chapter_top3": "|".join(_chapter_label(row) for row in ranked_top5[:3]),
        "chapter_hit_at_1": _as_bool_int(hit1),
        "chapter_hit_at_3": _as_bool_int(hit3),
        "chapter_hit_at_5": _as_bool_int(hit5),
        "retrieved_chunk_ids": _selected_chunk_ids(contexts),
        "evidence_terms_found": evidence_found,
        "evidence_terms_total": evidence_total,
        "context_recall": context_recall_like(contexts, evidence_terms),
        "context_precision": context_precision_like(contexts, evidence_terms),
        "failure_type": "",
        "_elapsed": elapsed,
        "_hit_for_retrieval": hit5,
    }


def _oracle_ranked(section: Optional[OracleSection]) -> List[Dict[str, object]]:
    if section is None:
        return []
    chapter = {
        "chapter_id": "oracle",
        "chapter_title": section.chapter_title,
        "start_char": section.start_char,
        "end_char": section.end_char,
    }
    return [chapter]


def _assign_failure_types(rows: List[Dict[str, object]]) -> None:
    by_question_method: Dict[Tuple[str, str], Dict[str, object]] = {
        (str(row["question_id"]), str(row["method"])): row for row in rows
    }

    for row in rows:
        method = str(row["method"])
        qid = str(row["question_id"])

        if method == "hier_current":
            baseline = by_question_method.get((qid, "hier_no_neighbors"))
            if baseline and (
                float(row["context_precision"]) < float(baseline["context_precision"]) - 1e-12
                or float(row["context_recall"]) < float(baseline["context_recall"]) - 1e-12
            ):
                row["failure_type"] = "neighbor_dilution"
                continue

        if method == "hier_oracle_chapter_neighbors":
            baseline = by_question_method.get((qid, "hier_oracle_chapter"))
            if baseline and (
                float(row["context_precision"]) < float(baseline["context_precision"]) - 1e-12
                or float(row["context_recall"]) < float(baseline["context_recall"]) - 1e-12
            ):
                row["failure_type"] = "neighbor_dilution"
                continue

        if not bool(row.get("_hit_for_retrieval")):
            row["failure_type"] = "wrong_chapter"
        elif int(row["evidence_terms_found"]) <= 0 and int(row["evidence_terms_total"]) > 0:
            row["failure_type"] = "right_chapter_wrong_chunk"
        else:
            row["failure_type"] = "ok"


def _summarize(rows: List[Dict[str, object]]) -> Dict[str, object]:
    by_method: "OrderedDict[str, List[Dict[str, object]]]" = OrderedDict()
    for row in rows:
        by_method.setdefault(str(row["method"]), []).append(row)

    method_summary: Dict[str, Dict[str, object]] = {}
    for method, method_rows in by_method.items():
        hit_rows = [row for row in method_rows if int(row["chapter_hit_at_5"]) == 1]
        miss_rows = [row for row in method_rows if int(row["chapter_hit_at_5"]) == 0]
        method_summary[method] = {
            "questions": len(method_rows),
            "avg_context_recall": _avg(float(row["context_recall"]) for row in method_rows),
            "avg_context_precision": _avg(float(row["context_precision"]) for row in method_rows),
            "chapter_hit_at_1": _avg(int(row["chapter_hit_at_1"]) for row in method_rows),
            "chapter_hit_at_3": _avg(int(row["chapter_hit_at_3"]) for row in method_rows),
            "chapter_hit_at_5": _avg(int(row["chapter_hit_at_5"]) for row in method_rows),
            "conditional_recall_when_expected_chapter_hit_at_5": _avg(
                float(row["context_recall"]) for row in hit_rows
            ),
            "conditional_recall_when_expected_chapter_missed_at_5": _avg(
                float(row["context_recall"]) for row in miss_rows
            ),
            "failure_type_counts": dict(Counter(str(row["failure_type"]) for row in method_rows)),
            "avg_latency_seconds": _avg(float(row["_elapsed"]) for row in method_rows),
        }
    return method_summary


def _write_results_csv(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "question_id",
        "question",
        "expected_chapter",
        "method",
        "predicted_chapter_top1",
        "predicted_chapter_top3",
        "chapter_hit_at_1",
        "chapter_hit_at_3",
        "chapter_hit_at_5",
        "retrieved_chunk_ids",
        "evidence_terms_found",
        "evidence_terms_total",
        "context_recall",
        "context_precision",
        "failure_type",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _write_summary_md(summary: Dict[str, object], path: Path) -> None:
    lines = [
        "# Experiment C: Hierarchical Retrieval Ablation",
        "",
        "This ablation diagnoses failure modes inside the Mirelands 5-book corpus and 80-question protocol.",
        "It does not claim a universal property of hierarchical RAG.",
        "",
        "## Method Summary",
        "",
        "| method | context recall | context precision | hit@1 | hit@3 | hit@5 | recall if hit@5 | recall if miss@5 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    method_summary = dict(summary["method_summary"])
    for method, row in method_summary.items():
        lines.append(
            "| {method} | {recall:.4f} | {precision:.4f} | {hit1:.4f} | {hit3:.4f} | "
            "{hit5:.4f} | {hit_recall:.4f} | {miss_recall:.4f} |".format(
                method=method,
                recall=float(row["avg_context_recall"]),
                precision=float(row["avg_context_precision"]),
                hit1=float(row["chapter_hit_at_1"]),
                hit3=float(row["chapter_hit_at_3"]),
                hit5=float(row["chapter_hit_at_5"]),
                hit_recall=float(row["conditional_recall_when_expected_chapter_hit_at_5"]),
                miss_recall=float(row["conditional_recall_when_expected_chapter_missed_at_5"]),
            )
        )

    lines.extend(["", "## Failure Type Counts", ""])
    for method, row in method_summary.items():
        lines.append(f"### {method}")
        counts = dict(row["failure_type_counts"])
        if not counts:
            lines.append("- none: 0")
        else:
            for name, count in sorted(counts.items()):
                lines.append(f"- {name}: {count}")
        lines.append("")

    lines.extend(
        [
            "## Safe Conclusion",
            "",
            str(summary["safe_conclusion"]),
            "",
            "## Notes",
            "",
            f"- Questions: {summary['question_count']}",
            f"- Chunk count: {summary['chunk_count']}",
            f"- Detected chunker chapter count: {summary['detected_chapter_count']}",
            f"- Parsed oracle chapter/section count: {summary['oracle_section_count']}",
            f"- Oracle-mapped questions: {summary['oracle_mapping']['mapped_questions']}",
            f"- Oracle-unmapped questions: {summary['oracle_mapping']['unmapped_questions']}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ablation() -> Dict[str, object]:
    book_text = read_book_text(BOOK_PATH)
    oracle_sections = _parse_oracle_sections(book_text)
    oracle_lookup = _section_lookup(oracle_sections)

    chunks = chunk_book_file(
        BOOK_PATH,
        chunk_size_words=CHUNK_SIZE_WORDS,
        overlap_words=OVERLAP_WORDS,
    )
    embeddings, metadata = embed_texts(
        [str(chunk.get("text") or "") for chunk in chunks],
        preferred_backend=EMBEDDING_BACKEND,
    )
    metadata = dict(metadata)
    metadata["embedding_backend"] = EMBEDDING_BACKEND

    chapters = _attach_ranges(_build_chapter_records(chunks), chunks)
    embedding_backend = str(metadata.get("embedding_backend") or EMBEDDING_BACKEND)
    chapter_top_n = max(1, min(len(chapters), max(2, min(4, TOP_K))))
    questions = load_questions(QUESTIONS_PATH)

    rows: List[Dict[str, object]] = []
    unmapped_questions: List[str] = []

    for item in questions:
        question = str(item.get("question") or "")
        section = _expected_section(item, oracle_lookup)
        if section is None:
            unmapped_questions.append(str(item.get("id") or ""))

        ranked_top5 = _rank_chapters(
            question=question,
            chapters=chapters,
            embedding_backend=embedding_backend,
            top_n=5,
        )
        ranked_top5 = _attach_ranges(ranked_top5, chunks)
        selected_chapters = ranked_top5[:chapter_top_n]

        started = time.perf_counter()
        seed_chunks = _retrieve_within_chapters(
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            selected_chapters=selected_chapters,
            top_k=TOP_K,
        )
        current_contexts = _expand_neighbors(chunks, seed_chunks, max_contexts=TOP_K)
        rows.append(
            _base_row(
                question_item=item,
                method="hier_current",
                ranked_top5=ranked_top5,
                section=section,
                contexts=current_contexts,
                elapsed=time.perf_counter() - started,
            )
        )

        started = time.perf_counter()
        no_neighbor_contexts = _retrieve_within_chapters(
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            selected_chapters=selected_chapters,
            top_k=TOP_K,
        )
        rows.append(
            _base_row(
                question_item=item,
                method="hier_no_neighbors",
                ranked_top5=ranked_top5,
                section=section,
                contexts=no_neighbor_contexts,
                elapsed=time.perf_counter() - started,
            )
        )

        oracle_indices = _oracle_chunk_indices(chunks, section)
        oracle_ranked = _oracle_ranked(section)

        started = time.perf_counter()
        oracle_contexts = _retrieve_from_indices(
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            indices=oracle_indices,
            top_k=TOP_K,
        )
        rows.append(
            _base_row(
                question_item=item,
                method="hier_oracle_chapter",
                ranked_top5=oracle_ranked,
                section=section,
                contexts=oracle_contexts,
                elapsed=time.perf_counter() - started,
            )
        )

        started = time.perf_counter()
        oracle_seed_chunks = _retrieve_from_indices(
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            indices=oracle_indices,
            top_k=TOP_K,
        )
        oracle_neighbor_contexts = _expand_neighbors(chunks, oracle_seed_chunks, max_contexts=TOP_K)
        rows.append(
            _base_row(
                question_item=item,
                method="hier_oracle_chapter_neighbors",
                ranked_top5=oracle_ranked,
                section=section,
                contexts=oracle_neighbor_contexts,
                elapsed=time.perf_counter() - started,
            )
        )

        started = time.perf_counter()
        chain_contexts = _retrieve_within_chapters(
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            selected_chapters=selected_chapters,
            top_k=TOP_K,
        )
        rows.append(
            _base_row(
                question_item=item,
                method="chapter_summary_chain",
                ranked_top5=ranked_top5,
                section=section,
                contexts=chain_contexts,
                elapsed=time.perf_counter() - started,
            )
        )

    _assign_failure_types(rows)
    method_summary = _summarize(rows)

    safe_conclusion = (
        "Inside this corpus/protocol, the ablation separates first-stage chapter selection, "
        "in-chapter chunk retrieval, and neighbor expansion. If oracle-chapter variants exceed "
        "the current hierarchical run, that supports the error-compounding hypothesis for this "
        "benchmark: misses at the chapter stage can constrain later chunk retrieval to the wrong "
        "context. This is diagnostic evidence for the Mirelands 5-book setup, not a universal "
        "claim about hierarchical RAG."
    )
    summary: Dict[str, object] = {
        "experiment": "Experiment C: hierarchical retrieval ablation",
        "book": str(BOOK_PATH),
        "questions": str(QUESTIONS_PATH),
        "question_count": len(questions),
        "chunk_count": len(chunks),
        "detected_chapter_count": len(chapters),
        "oracle_section_count": len(oracle_sections),
        "embedding_backend": metadata.get("embedding_backend"),
        "top_k": TOP_K,
        "reference_experiment_b": {
            "hierarchical_book_rag_context_recall": 0.3365,
            "chapter_summary_chain_context_recall": 0.4771,
            "naive_first_context_context_recall": 0.1458,
        },
        "oracle_mapping": {
            "mapped_questions": len(questions) - len(unmapped_questions),
            "unmapped_questions": len(unmapped_questions),
            "unmapped_question_ids": unmapped_questions,
        },
        "method_summary": method_summary,
        "safe_conclusion": safe_conclusion,
        "outputs": {
            "results_csv": str(RESULTS_CSV),
            "summary_md": str(SUMMARY_MD),
            "summary_json": str(SUMMARY_JSON),
        },
    }

    _write_results_csv(rows, RESULTS_CSV)
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_summary_md(summary, SUMMARY_MD)
    return summary


def main() -> None:
    summary = run_ablation()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
