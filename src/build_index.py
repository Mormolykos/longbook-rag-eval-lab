from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from chunk_book import chunk_book_file, write_jsonl
from retrieve import embed_texts, maybe_write_faiss


def build_index_from_chunks(
    chunks: List[Dict[str, object]],
    out_dir: Path,
    embedding_backend: str = "auto",
) -> Tuple[List[Dict[str, object]], np.ndarray, Dict[str, object]]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    texts = [str(row.get("text") or "") for row in chunks]
    embeddings, metadata = embed_texts(texts, preferred_backend=embedding_backend)

    write_jsonl(chunks, out_dir / "chunks.jsonl")
    np.save(out_dir / "embeddings.npy", embeddings.astype(np.float32))

    metadata = dict(metadata)
    metadata["chunk_count"] = len(chunks)
    metadata["index_type"] = "numpy_cosine"
    metadata["faiss_index"] = False

    if maybe_write_faiss(embeddings, out_dir / "faiss.index"):
        metadata["faiss_index"] = True
        metadata["index_type"] = "faiss_inner_product"

    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return chunks, embeddings, metadata


def build_index_from_book(
    book_path: Path,
    out_dir: Path,
    chunk_size_words: int = 900,
    overlap_words: int = 120,
    embedding_backend: str = "auto",
) -> Tuple[List[Dict[str, object]], np.ndarray, Dict[str, object]]:
    chunks = chunk_book_file(
        Path(book_path),
        chunk_size_words=chunk_size_words,
        overlap_words=overlap_words,
    )
    chunks, embeddings, metadata = build_index_from_chunks(
        chunks,
        out_dir=Path(out_dir),
        embedding_backend=embedding_backend,
    )
    metadata["book_path"] = str(book_path)
    (Path(out_dir) / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return chunks, embeddings, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local long-book retrieval index.")
    parser.add_argument("--book", required=True, help="Path to a UTF-8 .txt or .docx book file.")
    parser.add_argument("--out", required=True, help="Output index/cache folder.")
    parser.add_argument("--chunk-size-words", type=int, default=900)
    parser.add_argument("--overlap-words", type=int, default=120)
    parser.add_argument(
        "--embedding-backend",
        default="auto",
        choices=["auto", "sentence_transformers", "hashing_numpy"],
    )
    args = parser.parse_args()

    chunks, _embeddings, metadata = build_index_from_book(
        Path(args.book),
        Path(args.out),
        chunk_size_words=args.chunk_size_words,
        overlap_words=args.overlap_words,
        embedding_backend=args.embedding_backend,
    )
    print(
        json.dumps(
            {
                "chunks": len(chunks),
                "out": args.out,
                "embedding_backend": metadata.get("embedding_backend"),
                "index_type": metadata.get("index_type"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
