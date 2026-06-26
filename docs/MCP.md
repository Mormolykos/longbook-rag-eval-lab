# Local MCP Server

`product_mvp/mcp_longbook_server.py` is a **local stdio MCP server** (`FastMCP`, server name
`longbook-proof-local`) that exposes the LongBook Verifier engine to MCP clients such as Claude Code
or Codex.

It runs **locally only**. The client launches it as a subprocess and exchanges JSON-RPC over
stdin/stdout. There is **no hosted, remote, or cloud MCP mode** — it operates on your local project
files and writes only inside allowlisted local folders.

## Install
```powershell
python -m pip install mcp
```
(Plus the engine dependencies from [`requirements.txt`](../requirements.txt).)

## Run
```powershell
python product_mvp\mcp_longbook_server.py
```
(Or [`scripts/run_mcp.bat`](../scripts/run_mcp.bat).)

## Client configuration
Add an entry to your MCP client's `mcpServers` config (see
[`mcp_config.example.json`](../mcp_config.example.json)) and replace `EDIT_THIS_PATH` with the
absolute path to your cloned repository:

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

## Tools
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

`run_eval` methods: `naive_first_context`, `naive_last_context`, `flat_chunk_rag`,
`chapter_summary_chain`, `hierarchical_book_rag`.

## Local operation & safety
- Expects the **local project files/data** (you provide the book/index inputs); it does not fetch
  anything from the network.
- **Allowlisted** local scripts only — no arbitrary shell commands, no `shell=True`.
- **Strict path checks**: reads confined to the project root; writes confined to `outputs/`,
  `reports/`, and `product_mvp/runs/`; paths containing `.env` / `secret` / `key` / `token` /
  `password` are rejected.
- Child scripts run with `stdin=DEVNULL` and a timeout; retrieval is deterministic (`hashing_numpy`).
- **No remote/hosted MCP support.**
