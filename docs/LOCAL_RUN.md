# Local Run (Windows-first)

Run the LongBook Verifier evaluation engine and its local web app on your own machine. Everything
here runs **locally**; no cloud account or API key is required.

## Prerequisites
- Python **3.10+**
- Windows PowerShell (commands below); macOS/Linux users can adapt the venv-activation line.

## 1. Create and activate a virtual environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```

## 2. Install dependencies
```powershell
pip install -r requirements.txt
```
This installs the engine + web-app dependencies (`numpy`, `python-docx`, `fastapi`, `uvicorn`,
`python-multipart`). The MCP server additionally needs `mcp` — see [MCP.md](MCP.md).

## 3. Run the local web app
From the repository root:
```powershell
python -m uvicorn product_mvp.server_longbook_verifier:app --host 127.0.0.1 --port 8078
```
(Or double-click / run [`scripts/run_web.bat`](../scripts/run_web.bat).)

## 4. Open the page
Visit **<http://127.0.0.1:8078/>**.

The bundled local page lets you upload:
- a **book / manuscript** (`.txt`, `.md`, or `.docx`),
- an **AI output** to verify (`.txt` or `.md`), and
- optionally a **golden-questions** file (`.jsonl` with `id`, `question`, `gold_answer`,
  `evidence_terms`).

It returns a grounding report (evidence overlap, repeated named terms, possible unsupported terms,
and — when questions are provided — evidence/answer-term coverage). Results are written under
`product_mvp/runs/` on your machine.

## Notes
- The engine is deterministic (`hashing_numpy`) and makes **no external model API calls**.
- Use documents you have the right to use; this repo ships **no** corpora or sample books.
