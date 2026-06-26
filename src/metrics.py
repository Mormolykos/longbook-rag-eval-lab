from __future__ import annotations

import re
from typing import Dict, Iterable, List


TERM_RE = re.compile(r"[A-Za-z0-9_]+")


def _norm(text: str) -> str:
    return " ".join(TERM_RE.findall(str(text or "").lower()))


def _terms(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    for value in values:
        term = _norm(value)
        if term and term not in out:
            out.append(term)
    return out


def _gold_terms(gold_answer: str, evidence_terms: Iterable[str]) -> List[str]:
    terms = _terms(evidence_terms)
    if terms:
        return terms

    words = [w for w in TERM_RE.findall(str(gold_answer or "").lower()) if len(w) >= 4]
    seen: List[str] = []
    for word in words:
        if word not in seen:
            seen.append(word)
    return seen[:12]


def _contains_term(text: str, term: str) -> bool:
    return _norm(term) in _norm(text)


def context_precision_like(retrieved_chunks: List[Dict[str, object]], evidence_terms: Iterable[str]) -> float:
    terms = _terms(evidence_terms)
    if not retrieved_chunks:
        return 0.0
    if not terms:
        return 0.0

    hits = 0
    for chunk in retrieved_chunks:
        text = str(chunk.get("text") or "")
        if any(_contains_term(text, term) for term in terms):
            hits += 1
    return hits / float(len(retrieved_chunks))


def context_recall_like(retrieved_chunks: List[Dict[str, object]], evidence_terms: Iterable[str]) -> float:
    terms = _terms(evidence_terms)
    if not terms:
        return 0.0
    context_text = " ".join(str(chunk.get("text") or "") for chunk in retrieved_chunks)
    hits = sum(1 for term in terms if _contains_term(context_text, term))
    return hits / float(len(terms))


def answer_contains_gold_terms(answer: str, gold_answer: str, evidence_terms: Iterable[str]) -> float:
    terms = _gold_terms(gold_answer, evidence_terms)
    if not terms:
        return 0.0
    hits = sum(1 for term in terms if _contains_term(answer, term))
    return hits / float(len(terms))


def chronology_error_flags(answer: str, question: str, context_chunks: List[Dict[str, object]]) -> List[str]:
    return []


def summary_coverage_terms(summary: str, expected_terms: Iterable[str]) -> float:
    terms = _terms(expected_terms)
    if not terms:
        return 0.0
    hits = sum(1 for term in terms if _contains_term(summary, term))
    return hits / float(len(terms))


def tokens_estimated(text: str) -> int:
    words = len(TERM_RE.findall(str(text or "")))
    return int(round(words * 1.33))


def compute_metrics(
    question_item: Dict[str, object],
    answer: str,
    retrieved_chunks: List[Dict[str, object]],
    latency_seconds: float,
) -> Dict[str, object]:
    evidence_terms = question_item.get("evidence_terms") or []
    if not isinstance(evidence_terms, list):
        evidence_terms = []

    context_text = " ".join(str(chunk.get("text") or "") for chunk in retrieved_chunks)
    flags = chronology_error_flags(
        answer=answer,
        question=str(question_item.get("question") or ""),
        context_chunks=retrieved_chunks,
    )

    return {
        "context_precision_like": context_precision_like(retrieved_chunks, evidence_terms),
        "context_recall_like": context_recall_like(retrieved_chunks, evidence_terms),
        "answer_contains_gold_terms": answer_contains_gold_terms(
            answer,
            str(question_item.get("gold_answer") or ""),
            evidence_terms,
        ),
        "chronology_error_flags": ";".join(flags),
        "summary_coverage_terms": summary_coverage_terms(answer, evidence_terms),
        "latency_seconds": float(latency_seconds),
        "tokens_estimated": tokens_estimated(context_text + " " + answer),
        "retrieved_chunk_count": len(retrieved_chunks),
    }
