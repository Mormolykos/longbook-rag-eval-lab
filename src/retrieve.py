from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def load_jsonl(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _tokens(text: str) -> List[str]:
    return TOKEN_RE.findall(str(text or "").lower())


def _stable_hash(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "little")


def normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    arr = np.asarray(matrix, dtype=np.float32)
    denom = np.linalg.norm(arr, axis=1, keepdims=True)
    denom = np.maximum(denom, 1e-12)
    return (arr / denom).astype(np.float32)


def hash_embed_texts(texts: Iterable[str], dim: int = 384) -> np.ndarray:
    dim = max(32, int(dim))
    if not isinstance(texts, list):
        texts = list(texts)

    vectors = np.zeros((len(texts), dim), dtype=np.float32)

    for row_idx, text in enumerate(texts):
        counts: Dict[str, int] = {}
        for token in _tokens(text):
            counts[token] = counts.get(token, 0) + 1

        for token, count in counts.items():
            h = _stable_hash(token)
            col = h % dim
            sign = -1.0 if ((h >> 8) & 1) else 1.0
            vectors[row_idx, col] += sign * (1.0 + np.log1p(float(count)))

    return normalize_matrix(vectors)


def _try_sentence_transformers(texts: List[str]) -> Tuple[Optional[np.ndarray], Optional[Dict[str, object]]]:
    if importlib.util.find_spec("sentence_transformers") is None:
        return None, None

    from sentence_transformers import SentenceTransformer

    model_ref = os.getenv("LBRE_EMBED_MODEL_PATH") or os.getenv(
        "LBRE_EMBED_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )

    try:
        if os.getenv("LBRE_EMBED_MODEL_PATH"):
            model = SentenceTransformer(model_ref)
        else:
            model = SentenceTransformer(model_ref, local_files_only=True)
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except TypeError:
        return None, None
    except Exception:
        return None, None

    metadata = {
        "embedding_backend": "sentence_transformers",
        "embedding_model": model_ref,
        "embedding_dim": int(vectors.shape[1]),
    }
    return np.asarray(vectors, dtype=np.float32), metadata


def embed_texts(texts: Iterable[str], preferred_backend: str = "auto") -> Tuple[np.ndarray, Dict[str, object]]:
    text_list = [str(t or "") for t in texts]
    backend = str(preferred_backend or "auto").lower()

    if backend in {"auto", "sentence_transformers"}:
        vectors, metadata = _try_sentence_transformers(text_list)
        if vectors is not None and metadata is not None:
            return vectors, metadata
        if backend == "sentence_transformers":
            raise RuntimeError("sentence-transformers backend requested but no local model was available")

    dim = int(os.getenv("LBRE_HASH_DIM", "384"))
    vectors = hash_embed_texts(text_list, dim=dim)
    return vectors, {
        "embedding_backend": "hashing_numpy",
        "embedding_model": "stable_hash_bow",
        "embedding_dim": int(vectors.shape[1]),
    }


def maybe_write_faiss(embeddings: np.ndarray, out_path: Path) -> bool:
    if importlib.util.find_spec("faiss") is None:
        return False

    try:
        import faiss

        matrix = normalize_matrix(embeddings)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        faiss.write_index(index, str(out_path))
        return True
    except Exception:
        return False


def retrieve_from_embeddings(
    query: str,
    chunks: List[Dict[str, object]],
    embeddings: np.ndarray,
    metadata: Dict[str, object],
    top_k: int = 5,
) -> List[Dict[str, object]]:
    if not chunks:
        return []

    top_k = max(1, min(int(top_k), len(chunks)))
    backend = str(metadata.get("embedding_backend") or "hashing_numpy")
    query_vec, _query_meta = embed_texts([query], preferred_backend=backend)

    matrix = normalize_matrix(embeddings)
    scores = matrix @ query_vec[0]
    top_idx = np.argsort(-scores)[:top_k]

    out: List[Dict[str, object]] = []
    for idx in top_idx:
        row = dict(chunks[int(idx)])
        row["score"] = float(scores[int(idx)])
        out.append(row)
    return out


def retrieve_from_run(index_dir: Path, query: str, top_k: int = 5) -> List[Dict[str, object]]:
    index_dir = Path(index_dir)
    chunks = load_jsonl(index_dir / "chunks.jsonl")
    embeddings = np.load(index_dir / "embeddings.npy")
    metadata = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
    return retrieve_from_embeddings(query, chunks, embeddings, metadata, top_k=top_k)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve long-book chunks for a query.")
    parser.add_argument("--index", required=True, help="Index folder created by build_index.py.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    rows = retrieve_from_run(Path(args.index), args.query, top_k=args.top_k)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
