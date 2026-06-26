from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import time
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from build_index import build_index_from_book
from chunk_book import chunk_book_file
from metrics import compute_metrics
from retrieve import embed_texts, normalize_matrix, retrieve_from_embeddings


METHODS = {
    "naive_first_context",
    "naive_last_context",
    "flat_chunk_rag",
    "chapter_summary_chain",
    "hierarchical_book_rag",
}

WORD_RE = re.compile(r"[A-Za-z0-9_']+")
NAMED_TERM_RE = re.compile(r"\b[A-Z][A-Za-z']+(?:\s+[A-Z][A-Za-z']+){0,3}\b")
STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "because",
    "before",
    "being",
    "between",
    "chapter",
    "could",
    "every",
    "first",
    "from",
    "have",
    "into",
    "last",
    "like",
    "more",
    "only",
    "other",
    "over",
    "part",
    "same",
    "some",
    "than",
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


def load_questions(path: Path) -> List[Dict[str, object]]:
    questions: List[Dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row.setdefault("id", f"q{line_no:03d}")
            row.setdefault("evidence_terms", [])
            questions.append(row)
    return questions


def write_jsonl(rows: List[Dict[str, object]], path: Path) -> None:
    with Path(path).open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _tokens(text: str) -> List[str]:
    tokens = [t.lower().strip("'") for t in WORD_RE.findall(str(text or ""))]
    return [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]


def _unique(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        key = str(value)
        if key and key not in seen:
            out.append(key)
            seen.add(key)
    return out


def _truncate(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _paragraphs(text: str) -> List[str]:
    raw = re.split(r"\n\s*\n+", str(text or ""))
    paras = [" ".join(p.split()) for p in raw]
    return [p for p in paras if len(p) >= 40]


def _named_terms(text: str, limit: int = 24) -> List[str]:
    counts: Counter[str] = Counter()
    for match in NAMED_TERM_RE.findall(str(text or "")):
        term = " ".join(match.split())
        if term.lower() not in STOPWORDS and len(term) > 2:
            counts[term] += 1
    return [term for term, _count in counts.most_common(limit)]


def _lexical_score(query: str, text: str) -> float:
    query_terms = _tokens(query)
    if not query_terms:
        return 0.0

    text_counts = Counter(_tokens(text))
    if not text_counts:
        return 0.0

    weighted_hits = 0.0
    for term in query_terms:
        weighted_hits += min(3.0, float(text_counts.get(term, 0)))

    return weighted_hits / float(len(query_terms) * 3.0)


def _normalize_scores(scores: np.ndarray) -> np.ndarray:
    arr = np.asarray(scores, dtype=np.float32)
    if arr.size == 0:
        return arr
    lo = float(np.min(arr))
    hi = float(np.max(arr))
    if hi - lo < 1e-9:
        return np.ones_like(arr, dtype=np.float32) if hi > 0 else np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def _embed_similarity_scores(
    query: str,
    texts: List[str],
    embedding_backend: str,
) -> Tuple[np.ndarray, Dict[str, object]]:
    if not texts:
        return np.zeros((0,), dtype=np.float32), {"embedding_backend": embedding_backend}

    try:
        text_vectors, meta = embed_texts(texts, preferred_backend=embedding_backend)
        query_vector, _query_meta = embed_texts([query], preferred_backend=str(meta.get("embedding_backend") or embedding_backend))
    except Exception:
        text_vectors, meta = embed_texts(texts, preferred_backend="hashing_numpy")
        query_vector, _query_meta = embed_texts([query], preferred_backend="hashing_numpy")

    scores = normalize_matrix(text_vectors) @ normalize_matrix(query_vector)[0]
    return scores.astype(np.float32), meta


def _build_chapter_records(chunks: List[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: "OrderedDict[str, Dict[str, object]]" = OrderedDict()

    for idx, chunk in enumerate(chunks):
        chapter_id = str(chunk.get("chapter_id") or "unknown")
        if chapter_id not in grouped:
            grouped[chapter_id] = {
                "chapter_id": chapter_id,
                "chapter_title": str(chunk.get("chapter_title") or chapter_id),
                "chunks": [],
                "chunk_indices": [],
            }
        grouped[chapter_id]["chunks"].append(chunk)
        grouped[chapter_id]["chunk_indices"].append(idx)

    chapters: List[Dict[str, object]] = []
    for row in grouped.values():
        chapter_chunks = list(row["chunks"])
        text = "\n\n".join(str(chunk.get("text") or "") for chunk in chapter_chunks)
        chapters.append(
            {
                "chapter_id": row["chapter_id"],
                "chapter_title": row["chapter_title"],
                "chunks": chapter_chunks,
                "chunk_indices": list(row["chunk_indices"]),
                "text": text,
                "word_count": sum(int(chunk.get("word_count") or 0) for chunk in chapter_chunks),
            }
        )

    return chapters


def _question_focused_paragraphs(paragraphs: List[str], question: str, limit: int = 2) -> List[str]:
    scored = []
    for idx, paragraph in enumerate(paragraphs):
        score = _lexical_score(question, paragraph)
        if score > 0:
            scored.append((score, idx, paragraph))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [p for _score, _idx, p in scored[:limit]]


def _chapter_summary(chapter: Dict[str, object], question: str = "") -> str:
    text = str(chapter.get("text") or "")
    paragraphs = _paragraphs(text)
    first_parts = paragraphs[:2]
    last_parts = paragraphs[-1:] if len(paragraphs) > 2 else []
    focused_parts = _question_focused_paragraphs(paragraphs, question, limit=2)
    named = _named_terms(text, limit=18)

    parts = [
        f"chapter_id: {chapter.get('chapter_id')}",
        f"title: {chapter.get('chapter_title')}",
    ]
    if named:
        parts.append("named_terms: " + ", ".join(named))
    for label, group in (
        ("opening", first_parts),
        ("question_overlap", focused_parts),
        ("ending", last_parts),
    ):
        if group:
            parts.append(label + ": " + " ".join(_truncate(p, 450) for p in group))

    return "\n".join(parts)


def _rank_chapters(
    question: str,
    chapters: List[Dict[str, object]],
    embedding_backend: str,
    top_n: int,
) -> List[Dict[str, object]]:
    if not chapters:
        return []

    summaries = [_chapter_summary(chapter, question) for chapter in chapters]
    embed_scores, _meta = _embed_similarity_scores(question, summaries, embedding_backend)
    lexical_scores = np.asarray([_lexical_score(question, summary) for summary in summaries], dtype=np.float32)
    combined = (0.72 * _normalize_scores(embed_scores)) + (0.28 * _normalize_scores(lexical_scores))

    ranked: List[Dict[str, object]] = []
    for idx in np.argsort(-combined):
        chapter = dict(chapters[int(idx)])
        chapter["chapter_score"] = float(combined[int(idx)])
        chapter["chapter_embedding_score"] = float(embed_scores[int(idx)])
        chapter["chapter_lexical_score"] = float(lexical_scores[int(idx)])
        chapter["chapter_summary"] = summaries[int(idx)]
        ranked.append(chapter)

    return ranked[: max(1, min(int(top_n), len(ranked)))]


def _candidate_chunks_and_embeddings(
    chunks: List[Dict[str, object]],
    embeddings: np.ndarray,
    selected_chapters: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], np.ndarray]:
    allowed = {str(chapter.get("chapter_id") or "") for chapter in selected_chapters}
    candidate_chunks: List[Dict[str, object]] = []
    candidate_indices: List[int] = []

    for idx, chunk in enumerate(chunks):
        if str(chunk.get("chapter_id") or "") in allowed:
            candidate_chunks.append(dict(chunk))
            candidate_indices.append(idx)

    if not candidate_indices:
        return [], np.zeros((0, int(embeddings.shape[1]) if getattr(embeddings, "ndim", 0) == 2 else 1), dtype=np.float32)

    return candidate_chunks, np.asarray(embeddings[candidate_indices], dtype=np.float32)


def _retrieve_within_chapters(
    question: str,
    chunks: List[Dict[str, object]],
    embeddings: np.ndarray,
    metadata: Dict[str, object],
    selected_chapters: List[Dict[str, object]],
    top_k: int,
) -> List[Dict[str, object]]:
    candidate_chunks, candidate_embeddings = _candidate_chunks_and_embeddings(chunks, embeddings, selected_chapters)
    if not candidate_chunks:
        return []
    return retrieve_from_embeddings(question, candidate_chunks, candidate_embeddings, metadata, top_k=top_k)


def _expand_neighbors(
    chunks: List[Dict[str, object]],
    seed_chunks: List[Dict[str, object]],
    max_contexts: int,
) -> List[Dict[str, object]]:
    id_to_pos = {str(chunk.get("id") or ""): idx for idx, chunk in enumerate(chunks)}
    out: List[Dict[str, object]] = []
    seen = set()

    for seed in seed_chunks:
        seed_id = str(seed.get("id") or "")
        if seed_id not in id_to_pos:
            continue

        pos = id_to_pos[seed_id]
        seed_chapter = str(seed.get("chapter_id") or "")
        for neighbor_pos in (pos - 1, pos, pos + 1):
            if neighbor_pos < 0 or neighbor_pos >= len(chunks):
                continue
            neighbor = chunks[neighbor_pos]
            if str(neighbor.get("chapter_id") or "") != seed_chapter:
                continue

            neighbor_id = str(neighbor.get("id") or "")
            if neighbor_id in seen:
                continue

            row = dict(neighbor)
            if neighbor_id == seed_id:
                row["score"] = seed.get("score")
                row["retrieval_role"] = "seed"
            else:
                row["score"] = seed.get("score")
                row["retrieval_role"] = "neighbor"
            out.append(row)
            seen.add(neighbor_id)

            if len(out) >= max_contexts:
                return out

    return out


def _compose_extractive_answer(question: str, contexts: List[Dict[str, object]], method: str) -> str:
    snippets = []
    for chunk in contexts[:3]:
        text = " ".join(str(chunk.get("text") or "").split())
        snippets.append(text[:550])

    if not snippets:
        return f"{method}: no supporting context retrieved for '{question}'."

    joined = " ".join(snippets)
    return f"{method}: extractive evidence for '{question}'. {joined}"[:2000]


def _selected_ids(contexts: List[Dict[str, object]], key: str) -> List[str]:
    return _unique([str(row.get(key) or "") for row in contexts])


def _select_contexts(
    method: str,
    question: str,
    chunks: List[Dict[str, object]],
    embeddings: np.ndarray,
    metadata: Dict[str, object],
    top_k: int,
) -> Dict[str, object]:
    top_k = max(1, int(top_k))
    chapters = _build_chapter_records(chunks)
    embedding_backend = str(metadata.get("embedding_backend") or "hashing_numpy")
    chapter_top_n = max(1, min(len(chapters), max(2, min(4, top_k))))

    if method == "naive_first_context":
        contexts = [dict(row) for row in chunks[:top_k]]
        return {
            "contexts": contexts,
            "method_note": "first chunks from book",
            "selected_chapters": _selected_ids(contexts, "chapter_id"),
            "selected_chunk_ids": _selected_ids(contexts, "id"),
            "chapter_scores": [],
        }

    if method == "naive_last_context":
        contexts = [dict(row) for row in chunks[-top_k:]]
        return {
            "contexts": contexts,
            "method_note": "last chunks from book",
            "selected_chapters": _selected_ids(contexts, "chapter_id"),
            "selected_chunk_ids": _selected_ids(contexts, "id"),
            "chapter_scores": [],
        }

    if method == "flat_chunk_rag":
        contexts = retrieve_from_embeddings(question, chunks, embeddings, metadata, top_k=top_k)
        return {
            "contexts": contexts,
            "method_note": "single-level chunk retrieval across the whole book",
            "selected_chapters": _selected_ids(contexts, "chapter_id"),
            "selected_chunk_ids": _selected_ids(contexts, "id"),
            "chapter_scores": [],
        }

    selected_chapters = _rank_chapters(
        question=question,
        chapters=chapters,
        embedding_backend=embedding_backend,
        top_n=chapter_top_n,
    )

    if method == "chapter_summary_chain":
        contexts = _retrieve_within_chapters(
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            selected_chapters=selected_chapters,
            top_k=top_k,
        )
        return {
            "contexts": contexts,
            "method_note": "chapter summaries ranked first, then chunks selected from the best chapters",
            "selected_chapters": [str(chapter.get("chapter_id") or "") for chapter in selected_chapters],
            "selected_chunk_ids": _selected_ids(contexts, "id"),
            "chapter_scores": [
                {
                    "chapter_id": chapter.get("chapter_id"),
                    "score": chapter.get("chapter_score"),
                    "embedding_score": chapter.get("chapter_embedding_score"),
                    "lexical_score": chapter.get("chapter_lexical_score"),
                }
                for chapter in selected_chapters
            ],
        }

    if method == "hierarchical_book_rag":
        seed_chunks = _retrieve_within_chapters(
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            selected_chapters=selected_chapters,
            top_k=top_k,
        )
        contexts = _expand_neighbors(chunks, seed_chunks, max_contexts=top_k)
        return {
            "contexts": contexts,
            "method_note": "chapter-ranked retrieval with in-chapter chunk search and neighbor expansion",
            "selected_chapters": [str(chapter.get("chapter_id") or "") for chapter in selected_chapters],
            "selected_chunk_ids": _selected_ids(contexts, "id"),
            "chapter_scores": [
                {
                    "chapter_id": chapter.get("chapter_id"),
                    "score": chapter.get("chapter_score"),
                    "embedding_score": chapter.get("chapter_embedding_score"),
                    "lexical_score": chapter.get("chapter_lexical_score"),
                }
                for chapter in selected_chapters
            ],
        }

    raise ValueError(f"Unknown method: {method}")


def summarize(rows: List[Dict[str, object]], method: str) -> Dict[str, object]:
    def avg(key: str) -> float:
        vals = [float(row.get(key) or 0.0) for row in rows]
        return float(statistics.fmean(vals)) if vals else 0.0

    return {
        "method": method,
        "count": len(rows),
        "avg_context_precision": avg("context_precision_like"),
        "avg_context_recall": avg("context_recall_like"),
        "avg_answer_score": avg("answer_contains_gold_terms"),
        "avg_latency": avg("latency_seconds"),
        "avg_tokens": avg("tokens_estimated"),
    }


def run_eval(
    book: Path,
    questions_path: Path,
    method: str,
    out: Path,
    top_k: int = 5,
    chunk_size_words: int = 900,
    overlap_words: int = 120,
    embedding_backend: str = "auto",
) -> Dict[str, object]:
    if method not in METHODS:
        raise ValueError(f"method must be one of: {', '.join(sorted(METHODS))}")

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    index_dir = out / "index"

    if method in {"flat_chunk_rag", "chapter_summary_chain", "hierarchical_book_rag"}:
        chunks, embeddings, metadata = build_index_from_book(
            book,
            index_dir,
            chunk_size_words=chunk_size_words,
            overlap_words=overlap_words,
            embedding_backend=embedding_backend,
        )
    else:
        chunks = chunk_book_file(
            book,
            chunk_size_words=chunk_size_words,
            overlap_words=overlap_words,
        )
        chunks, embeddings, metadata = build_index_from_book(
            book,
            index_dir,
            chunk_size_words=chunk_size_words,
            overlap_words=overlap_words,
            embedding_backend="hashing_numpy",
        )

    questions = load_questions(questions_path)
    results: List[Dict[str, object]] = []
    metric_rows: List[Dict[str, object]] = []

    for item in questions:
        question = str(item.get("question") or "")
        started = time.perf_counter()
        selected = _select_contexts(
            method=method,
            question=question,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            top_k=top_k,
        )
        contexts = list(selected["contexts"])
        answer = _compose_extractive_answer(question, contexts, method)
        latency = time.perf_counter() - started

        metric_row = compute_metrics(item, answer, contexts, latency)
        metric_row["id"] = item.get("id")
        metric_row["method"] = method
        metric_row["selected_chapters"] = "|".join(str(x) for x in selected["selected_chapters"])
        metric_row["selected_chunk_ids"] = "|".join(str(x) for x in selected["selected_chunk_ids"])
        metric_rows.append(metric_row)

        results.append(
            {
                "id": item.get("id"),
                "method": method,
                "question": question,
                "gold_answer": item.get("gold_answer", ""),
                "expected_chapter": item.get("expected_chapter", ""),
                "answer": answer,
                "method_note": selected["method_note"],
                "selected_chapters": selected["selected_chapters"],
                "selected_chunk_ids": selected["selected_chunk_ids"],
                "retrieved_chunk_count": metric_row["retrieved_chunk_count"],
                "tokens_estimated": metric_row["tokens_estimated"],
                "latency_seconds": metric_row["latency_seconds"],
                "chapter_scores": selected["chapter_scores"],
                "retrieved_chunks": [
                    {
                        "id": row.get("id"),
                        "chapter_id": row.get("chapter_id"),
                        "chapter_title": row.get("chapter_title"),
                        "start_char": row.get("start_char"),
                        "end_char": row.get("end_char"),
                        "word_count": row.get("word_count"),
                        "score": row.get("score"),
                        "retrieval_role": row.get("retrieval_role", "retrieved"),
                    }
                    for row in contexts
                ],
                "metrics": metric_row,
            }
        )

    write_jsonl(results, out / "results.jsonl")

    fieldnames = [
        "id",
        "method",
        "selected_chapters",
        "selected_chunk_ids",
        "context_precision_like",
        "context_recall_like",
        "answer_contains_gold_terms",
        "chronology_error_flags",
        "summary_coverage_terms",
        "latency_seconds",
        "tokens_estimated",
        "retrieved_chunk_count",
    ]
    with (out / "metrics.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in metric_rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    summary = summarize(metric_rows, method)
    summary["book"] = str(book)
    summary["questions"] = str(questions_path)
    summary["top_k"] = int(top_k)
    summary["chunk_count"] = len(chunks)
    summary["chapter_count"] = len(_build_chapter_records(chunks))
    summary["embedding_backend"] = metadata.get("embedding_backend")
    summary["method_description"] = {
        "naive_first_context": "first chunks from the book",
        "naive_last_context": "last chunks from the book",
        "flat_chunk_rag": "single-level chunk retrieval",
        "chapter_summary_chain": "chapter summary ranking followed by in-chapter chunk retrieval",
        "hierarchical_book_rag": "chapter scoring, in-chapter chunk retrieval, and neighbor expansion",
    }.get(method, method)
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run long-book RAG evaluation.")
    parser.add_argument("--book", required=True, help="Input UTF-8 .txt or .docx book.")
    parser.add_argument("--questions", required=True, help="Questions JSONL file.")
    parser.add_argument("--method", required=True, choices=sorted(METHODS))
    parser.add_argument("--out", required=True, help="Output run folder.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--chunk-size-words", type=int, default=900)
    parser.add_argument("--overlap-words", type=int, default=120)
    parser.add_argument(
        "--embedding-backend",
        default="auto",
        choices=["auto", "sentence_transformers", "hashing_numpy"],
    )
    args = parser.parse_args()

    summary = run_eval(
        book=Path(args.book),
        questions_path=Path(args.questions),
        method=args.method,
        out=Path(args.out),
        top_k=args.top_k,
        chunk_size_words=args.chunk_size_words,
        overlap_words=args.overlap_words,
        embedding_backend=args.embedding_backend,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
