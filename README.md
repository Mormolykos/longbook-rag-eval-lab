# LongBook Verifier

**An MCP-enabled evaluation and claim-grounding toolkit for long-document RAG systems.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20513116-blue.svg)](https://doi.org/10.5281/zenodo.20513116)
[![Live demo: BookProof](https://img.shields.io/badge/demo-BookProof-brightgreen.svg)](https://tts.bedvibe.studio/bookproof/app/)
![MCP: local stdio](https://img.shields.io/badge/MCP-local%20stdio-purple.svg)

LongBook Verifier measures whether retrieval methods and AI outputs are actually *grounded* in
long narrative manuscripts — by retrieving evidence from the document and scoring coverage,
deterministically and without external model APIs.

## Use it three ways

| | What you get | For |
|---|---|---|
| 🔌 **Local MCP** | A local **stdio** MCP server for **Claude Code / Codex** — long-document evaluation, retrieval, claim verification, and report tools. **Local only** (not hosted or remote). → **[docs/MCP.md](docs/MCP.md)** | Using the verifier as tools inside your AI client |
| 🌐 **Try BookProof online** | The **live hosted web product** — upload a document + golden questions in the browser, no install. → **[tts.bedvibe.studio/bookproof/app](https://tts.bedvibe.studio/bookproof/app/)** | Trying it instantly |
| 💻 **Run locally** | Clone and run the FastAPI web app + evaluation engine on your own machine. → **[docs/LOCAL_RUN.md](docs/LOCAL_RUN.md)** | Developers / researchers inspecting or running the verifier |

## What it does

- **Retrieval evaluation** across five methods — `naive_first_context`, `naive_last_context`,
  `flat_chunk_rag`, `chapter_summary_chain`, `hierarchical_book_rag` — on book-length documents.
- **Claim / answer grounding**: scores an AI output (or a set of claims/questions) against the
  source document using evidence-term coverage, answer-term coverage, and retrieval
  context precision/recall–like metrics.
- **Deterministic** local embeddings (`hashing_numpy`) — reproducible, no downloaded models and no
  Claude/OpenAI/Gemini calls.
- Three ways to use the same engine: a **CLI/eval pipeline**, a **local FastAPI web app**, and a
  **local stdio MCP server** for AI coding clients.

## Why it exists

Short-answer correctness and *evidence grounding* can diverge: a model can give a plausible answer
that the document doesn't actually support. LongBook Verifier separates those signals so you can
audit whether outputs and retrieval are grounded in long manuscripts — useful for manuscript QA and
reproducible long-document evaluation.

## Live product

A hosted, public version of this evaluation runs as **BookProof**:

➡️ **[BookProof — try it online](https://tts.bedvibe.studio/bookproof/app/)**

BookProof is an existing, related public product. It is **not required** to run anything in this
repository locally.

## Architecture

One evaluation engine, three access surfaces, plus the hosted product:

- **Research / evaluation engine** (`src/`) — chunking, deterministic index build, retrieval, the
  five methods, metrics, and claim verification.
- **Local FastAPI web app** (`product_mvp/server_longbook_verifier.py`) — upload a document +
  golden questions in the browser and get scored locally.
- **Local stdio MCP server** (`product_mvp/mcp_longbook_server.py`) — exposes the engine to MCP
  clients (e.g. Claude Code / Codex) over stdio, **locally only**.
- **BookProof public product/API** — a deployed instance offering a rate-limited public demo and a
  separate token-gated verification API (see [BookProof API](#bookproof-api)).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a diagram.

## Research methods

The benchmark reports **evidence-term coverage, answer-term coverage, retrieval context recall, and
task-completion behavior separately** — because short-answer correctness and evidence grounding can
diverge. Two experiments are documented in [`paper/`](paper/):

- **Experiment A** — a pilot single-book benchmark (~64k words, 40 gold questions, 5 retrieval
  methods, 5 external consumer AI systems under a free-tier protocol).
- **Experiment B** — an extended stress test on a 240,767-word corpus (~320,220 tokens, 80 gold
  questions, 5 retrieval methods).

These are a **pilot plus stress-test package**, *not* a universal model ranking or state-of-the-art
claim. Full methods and results are in [`paper/`](paper/); the research package is archived at
**DOI [10.5281/zenodo.20513116](https://doi.org/10.5281/zenodo.20513116)**.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Details: [docs/LOCAL_RUN.md](docs/LOCAL_RUN.md).

## Run the local web app

```powershell
python -m uvicorn product_mvp.server_longbook_verifier:app --host 127.0.0.1 --port 8078
```

Then open **<http://127.0.0.1:8078/>** and upload a document + golden questions.

## Use the local MCP server

```powershell
python product_mvp\mcp_longbook_server.py
```

The MCP server runs **locally over stdio**; an MCP client launches it as a subprocess. It also
requires the `mcp` package: `python -m pip install mcp`. See [docs/MCP.md](docs/MCP.md).

## MCP client configuration

Generic `mcpServers` entry (replace the path with the location of your cloned repo — see
[`mcp_config.example.json`](mcp_config.example.json)):

```json
{
  "mcpServers": {
    "longbook-proof-local": {
      "command": "python",
      "args": ["EDIT_THIS_PATH/product_mvp/mcp_longbook_server.py"]
    }
  }
}
```

## MCP tools

All tools are **read-or-allowlisted, local-only**:

| Tool | Description |
|---|---|
| `longbook_status` | Read-only project summary (allowed roots, scripts, report/run counts, default backend). |
| `list_books` | List `.txt` / `.md` / `.docx` files under the project book folder (or a sub-path inside the project). |
| `list_reports` | List report-like files (`.md` / `.txt` / `.json` / `.jsonl` / `.csv`). |
| `read_report` | Read a report-like file with truncation. |
| `run_chunking` | Chunk a book into a `.jsonl` (`src/chunk_book.py`). |
| `run_index_build` | Build a retrieval index (`src/build_index.py`, `hashing_numpy`). |
| `run_retrieve` | Return ranked chunks from an existing local index (`src/retrieve.py`). |
| `run_eval` | Run a retrieval-evaluation method over a book + questions (`src/run_eval.py`). |
| `generate_report_tables` | Build summary CSV tables from run folders (`src/report_tables.py`). |

## Repository structure

```text
src/             evaluation engine (chunking, index, retrieval, methods, metrics, claim checks)
product_mvp/     local FastAPI web app + local stdio MCP server + site/ frontend
paper/           research write-ups (methods, results, limitations) + CITATION.cff
docs/            LOCAL_RUN, MCP, ARCHITECTURE
scripts/         Windows helpers (run_web.bat, run_mcp.bat)
```

## Data policy

Copyrighted corpora, source manuscripts, private evaluation data, and user uploads are
**intentionally excluded** from this repository. The tools operate on documents **you** provide.

## Security model

Confirmed in `product_mvp/mcp_longbook_server.py`: the MCP server runs **local stdio only** and
calls an **allowlisted** set of local scripts. It uses **no arbitrary shell commands** (no
`shell=True`), enforces **strict read/write path checks** (reads confined to the project root;
writes confined to `outputs/`, `reports/`, and `product_mvp/runs/`), **rejects** paths containing
`.env` / `secret` / `key` / `token` / `password`, runs child scripts with `stdin=DEVNULL`, applies a
timeout, and makes **no cloud or external model calls**. It does **not** provide shell execution or
remote access.

## BookProof API

The hosted **[BookProof](https://tts.bedvibe.studio/bookproof/app/)** product exposes:

- a **public, rate-limited demo** endpoint (capped document size, capped questions, one run per IP
  per day, inputs deleted after processing), and
- a separate **token-gated verification API** (authenticated via an `X-BookProof-Token` header) with
  a machine-readable spec endpoint.

No token is included in this repository.

## Limitations

- Evaluation is **lexical/retrieval-based and deterministic** (`hashing_numpy`); it is not a
  semantic-embedding or model-graded benchmark.
- The published results are a **pilot + stress test**, not a universal ranking or SOTA claim.
- The MCP server expects the **local project files** and runs entirely on your machine.

## License

[MIT](LICENSE) © 2026 Panos Gkilis. Contact via
[GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories) for
security reports (see [SECURITY.md](SECURITY.md)).
