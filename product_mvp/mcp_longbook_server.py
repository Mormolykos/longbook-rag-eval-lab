"""Local MCP wrapper for the LongBook Proof / RAG evaluation lab.

This server exposes a small allowlisted set of local tools. It does not run
arbitrary shell commands, does not use shell=True, and does not call cloud APIs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - only hit before MCP install.
    raise SystemExit(
        "Missing Python package 'mcp'. Install it in this environment before "
        "running the LongBook MCP server: python -m pip install mcp"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = PROJECT_ROOT / "product_mvp"
SRC_DIR = PROJECT_ROOT / "src"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RUNS_DIR = OUTPUTS_DIR / "runs"
REPORTS_DIR = PROJECT_ROOT / "reports"
PRODUCT_RUNS_DIR = PRODUCT_DIR / "runs"
PROJECT_BOOKS_DIR = PROJECT_ROOT / "data" / "books"

ALLOWED_READ_ROOTS = tuple(
    root.resolve()
    for root in (
        PROJECT_ROOT,
    )
)

ALLOWED_WRITE_ROOTS = tuple(
    root.resolve()
    for root in (
        OUTPUTS_DIR,
        REPORTS_DIR,
        PRODUCT_RUNS_DIR,
    )
)

ALLOWLISTED_SCRIPTS = {
    (SRC_DIR / "chunk_book.py").resolve(),
    (SRC_DIR / "build_index.py").resolve(),
    (SRC_DIR / "retrieve.py").resolve(),
    (SRC_DIR / "run_eval.py").resolve(),
    (SRC_DIR / "report_tables.py").resolve(),
}

BLOCKED_NAME_RE = re.compile(r"(^|[._\-\s])(env|secret|key|token|password)([._\-\s]|$)", re.I)
BLOCKED_SUBSTRINGS = ("secret", "token", "password")
REPORT_EXTENSIONS = {".csv", ".json", ".jsonl", ".md", ".txt"}
BOOK_EXTENSIONS = {".docx", ".md", ".txt"}
QUESTION_EXTENSIONS = {".jsonl"}
CHUNK_EXTENSIONS = {".jsonl"}
VALID_METHODS = {
    "chapter_summary_chain",
    "flat_chunk_rag",
    "hierarchical_book_rag",
    "naive_first_context",
    "naive_last_context",
}

DEFAULT_STDOUT_LIMIT = 12_000
MAX_READ_CHARS = 100_000
MAX_TIMEOUT_SECONDS = 900

mcp = FastMCP("longbook-proof-local")


def _as_path(raw_path: str | Path) -> Path:
    return Path(raw_path).expanduser().resolve()


def _blocked_path_name(path: Path) -> bool:
    for part in path.parts:
        lower = part.lower()
        if lower == ".env" or BLOCKED_NAME_RE.search(lower):
            return True
        if any(term in lower for term in BLOCKED_SUBSTRINGS):
            return True
    return False


def _is_under(path: Path, roots: tuple[Path, ...]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _safe_read_path(raw_path: str | Path, *, must_exist: bool = True) -> Path:
    path = _as_path(raw_path)
    if _blocked_path_name(path):
        raise ValueError(f"Blocked sensitive-looking path: {path}")
    if not _is_under(path, ALLOWED_READ_ROOTS):
        raise ValueError(f"Read path is outside allowed roots: {path}")
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Read path does not exist: {path}")
    return path


def _safe_read_file(raw_path: str | Path, *, extensions: set[str] | None = None) -> Path:
    path = _safe_read_path(raw_path)
    if not path.is_file():
        raise ValueError(f"Expected file, got: {path}")
    if extensions is not None and path.suffix.lower() not in extensions:
        raise ValueError(f"Unsupported file extension for {path}; allowed: {sorted(extensions)}")
    return path


def _safe_read_dir(raw_path: str | Path, *, must_exist: bool = True) -> Path:
    path = _safe_read_path(raw_path, must_exist=must_exist)
    if must_exist and not path.is_dir():
        raise ValueError(f"Expected directory, got: {path}")
    return path


def _safe_write_path(raw_path: str | Path, *, extensions: set[str] | None = None) -> Path:
    path = _as_path(raw_path)
    if _blocked_path_name(path):
        raise ValueError(f"Blocked sensitive-looking output path: {path}")
    if not _is_under(path, ALLOWED_WRITE_ROOTS):
        raise ValueError(f"Write path is outside allowed roots: {path}")
    if extensions is not None and path.suffix.lower() not in extensions:
        raise ValueError(f"Unsupported output extension for {path}; allowed: {sorted(extensions)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _safe_write_dir(raw_path: str | Path) -> Path:
    path = _as_path(raw_path)
    if _blocked_path_name(path):
        raise ValueError(f"Blocked sensitive-looking output directory: {path}")
    if not _is_under(path, ALLOWED_WRITE_ROOTS):
        raise ValueError(f"Write directory is outside allowed roots: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_run_output_dir(raw_path: str | Path) -> Path:
    path = _safe_write_dir(raw_path)
    if not _is_under(path, (RUNS_DIR.resolve(),)):
        raise ValueError(f"Evaluation run output must be under {RUNS_DIR}: {path}")
    return path


def _safe_report_output(raw_path: str | Path) -> Path:
    path = _safe_write_path(raw_path, extensions=REPORT_EXTENSIONS)
    if not _is_under(path, (REPORTS_DIR.resolve(), PRODUCT_RUNS_DIR.resolve())):
        raise ValueError(f"Report output must be under reports or product_mvp/runs: {path}")
    return path


def _truncate(text: str, limit: int = DEFAULT_STDOUT_LIMIT) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n...[truncated]...", True


def _bounded_timeout(timeout_seconds: int) -> int:
    if timeout_seconds < 1:
        raise ValueError("timeout_seconds must be positive")
    return min(timeout_seconds, MAX_TIMEOUT_SECONDS)


def _run_python(script: Path, args: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    script = script.resolve()
    if script not in ALLOWLISTED_SCRIPTS:
        raise ValueError(f"Script is not allowlisted for MCP execution: {script}")
    if not script.exists():
        raise FileNotFoundError(f"Allowlisted script is missing: {script}")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_bounded_timeout(timeout_seconds),
        shell=False,
        env=env,
    )
    stdout, stdout_truncated = _truncate(completed.stdout)
    stderr, stderr_truncated = _truncate(completed.stderr)
    return {
        "returncode": completed.returncode,
        "script": str(script),
        "args": args,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }


def _file_summary(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "size_bytes": stat.st_size,
        "modified": stat.st_mtime,
    }


def _safe_files(root: Path, *, extensions: set[str], max_items: int) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    safe_root = _safe_read_dir(root)
    rows: list[dict[str, Any]] = []
    for path in sorted(safe_root.rglob("*")):
        if len(rows) >= max_items:
            break
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if _blocked_path_name(path):
            continue
        rows.append(_file_summary(path))
    return rows


def _safe_dirs(root: Path, *, max_items: int) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    safe_root = _safe_read_dir(root)
    rows: list[dict[str, Any]] = []
    for path in sorted(safe_root.iterdir()):
        if len(rows) >= max_items:
            break
        if not path.is_dir() or _blocked_path_name(path):
            continue
        stat = path.stat()
        rows.append({"path": str(path), "name": path.name, "modified": stat.st_mtime})
    return rows


@mcp.tool()
def longbook_status() -> dict[str, Any]:
    """Return read-only status for the local LongBook project."""
    return {
        "project_root": str(PROJECT_ROOT),
        "product_dir": str(PRODUCT_DIR),
        "read_roots": [str(path) for path in ALLOWED_READ_ROOTS],
        "write_roots": [str(path) for path in ALLOWED_WRITE_ROOTS],
        "allowlisted_scripts": [str(path) for path in sorted(ALLOWLISTED_SCRIPTS)],
        "intentionally_not_exposed": [
            str(SRC_DIR / "run_ablation.py"),
            str(SRC_DIR / "package_experiment_c_zenodo.py"),
        ],
        "books_count": len(_safe_files(PROJECT_BOOKS_DIR, extensions=BOOK_EXTENSIONS, max_items=500)),
        "report_count": len(_safe_files(REPORTS_DIR, extensions=REPORT_EXTENSIONS, max_items=1000)),
        "eval_run_count": len(_safe_dirs(RUNS_DIR, max_items=1000)),
        "product_run_count": len(_safe_dirs(PRODUCT_RUNS_DIR, max_items=1000)),
        "default_embedding_backend": "hashing_numpy",
    }


@mcp.tool()
def list_books(root: str | None = None, max_items: int = 200) -> dict[str, Any]:
    """List book/manuscript files under the project."""
    max_items = max(1, min(max_items, 1000))
    roots = [_safe_read_dir(root)] if root else [PROJECT_BOOKS_DIR]
    files: list[dict[str, Any]] = []
    for item in roots:
        files.extend(_safe_files(item, extensions=BOOK_EXTENSIONS, max_items=max_items - len(files)))
        if len(files) >= max_items:
            break
    return {"count": len(files), "files": files}


@mcp.tool()
def list_reports(root: str | None = None, max_items: int = 300) -> dict[str, Any]:
    """List report-like files under reports, outputs, or product runs."""
    max_items = max(1, min(max_items, 1000))
    roots = [_safe_read_dir(root)] if root else [REPORTS_DIR, RUNS_DIR, PRODUCT_RUNS_DIR]
    files: list[dict[str, Any]] = []
    for item in roots:
        files.extend(_safe_files(item, extensions=REPORT_EXTENSIONS, max_items=max_items - len(files)))
        if len(files) >= max_items:
            break
    return {"count": len(files), "files": files}


@mcp.tool()
def read_report(path: str, max_chars: int = 20_000) -> dict[str, Any]:
    """Read a report-like text file with truncation."""
    path_obj = _safe_read_file(path, extensions=REPORT_EXTENSIONS)
    limit = max(1, min(max_chars, MAX_READ_CHARS))
    content = path_obj.read_text(encoding="utf-8", errors="replace")
    truncated_content, truncated = _truncate(content, limit)
    return {
        "path": str(path_obj),
        "size_bytes": path_obj.stat().st_size,
        "truncated": truncated,
        "content": truncated_content,
    }


@mcp.tool()
def run_chunking(
    book: str,
    out: str,
    chunk_size_words: int = 900,
    overlap_words: int = 120,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Chunk a book into JSONL using the existing chunk_book.py script."""
    book_path = _safe_read_file(book, extensions=BOOK_EXTENSIONS)
    out_path = _safe_write_path(out, extensions=CHUNK_EXTENSIONS)
    args = [
        "--book",
        str(book_path),
        "--out",
        str(out_path),
        "--chunk-size-words",
        str(max(100, min(chunk_size_words, 3000))),
        "--overlap-words",
        str(max(0, min(overlap_words, 1000))),
    ]
    result = _run_python(SRC_DIR / "chunk_book.py", args, timeout_seconds=timeout_seconds)
    result["output_path"] = str(out_path)
    return result


@mcp.tool()
def run_index_build(
    book: str,
    out: str,
    chunk_size_words: int = 900,
    overlap_words: int = 120,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Build a deterministic local retrieval index with hashing_numpy."""
    book_path = _safe_read_file(book, extensions=BOOK_EXTENSIONS)
    out_dir = _safe_write_dir(out)
    args = [
        "--book",
        str(book_path),
        "--out",
        str(out_dir),
        "--chunk-size-words",
        str(max(100, min(chunk_size_words, 3000))),
        "--overlap-words",
        str(max(0, min(overlap_words, 1000))),
        "--embedding-backend",
        "hashing_numpy",
    ]
    result = _run_python(SRC_DIR / "build_index.py", args, timeout_seconds=timeout_seconds)
    result["output_dir"] = str(out_dir)
    result["embedding_backend"] = "hashing_numpy"
    return result


@mcp.tool()
def run_retrieve(index: str, query: str, top_k: int = 5, timeout_seconds: int = 60) -> dict[str, Any]:
    """Retrieve chunks from an existing local index."""
    index_dir = _safe_read_dir(index)
    if len(query) > 2000:
        raise ValueError("query is too long; maximum is 2000 characters")
    args = [
        "--index",
        str(index_dir),
        "--query",
        query,
        "--top-k",
        str(max(1, min(top_k, 20))),
    ]
    return _run_python(SRC_DIR / "retrieve.py", args, timeout_seconds=timeout_seconds)


@mcp.tool()
def run_eval(
    book: str,
    questions: str,
    method: str,
    out: str,
    top_k: int = 5,
    chunk_size_words: int = 900,
    overlap_words: int = 120,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    """Run one existing retrieval evaluation method with hashing_numpy."""
    if method not in VALID_METHODS:
        raise ValueError(f"Unsupported method: {method}. Allowed: {sorted(VALID_METHODS)}")
    book_path = _safe_read_file(book, extensions=BOOK_EXTENSIONS)
    questions_path = _safe_read_file(questions, extensions=QUESTION_EXTENSIONS)
    out_dir = _safe_run_output_dir(out)
    args = [
        "--book",
        str(book_path),
        "--questions",
        str(questions_path),
        "--method",
        method,
        "--out",
        str(out_dir),
        "--top-k",
        str(max(1, min(top_k, 20))),
        "--chunk-size-words",
        str(max(100, min(chunk_size_words, 3000))),
        "--overlap-words",
        str(max(0, min(overlap_words, 1000))),
        "--embedding-backend",
        "hashing_numpy",
    ]
    result = _run_python(SRC_DIR / "run_eval.py", args, timeout_seconds=timeout_seconds)
    result["output_dir"] = str(out_dir)
    result["embedding_backend"] = "hashing_numpy"
    return result


@mcp.tool()
def generate_report_tables(
    runs: list[str],
    out: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Build a comparison CSV from existing run folders."""
    if not runs:
        raise ValueError("At least one run folder is required")
    safe_runs = [_safe_read_dir(run) for run in runs]
    for run in safe_runs:
        if not _is_under(run, (RUNS_DIR.resolve(),)):
            raise ValueError(f"Run folder must be under {RUNS_DIR}: {run}")
    out_path = _safe_write_path(out or (REPORTS_DIR / "mcp_comparison.csv"), extensions={".csv"})
    if not _is_under(out_path, (REPORTS_DIR.resolve(),)):
        raise ValueError(f"Comparison CSV must be under {REPORTS_DIR}: {out_path}")

    args = ["--runs", *[str(run) for run in safe_runs], "--out", str(out_path)]
    result = _run_python(SRC_DIR / "report_tables.py", args, timeout_seconds=timeout_seconds)
    result["output_path"] = str(out_path)
    return result


if __name__ == "__main__":
    mcp.run()
