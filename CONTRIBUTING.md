# Contributing

Thanks for your interest. This is a research/evaluation toolkit; contributions that improve
correctness, reproducibility, docs, and tests are welcome.

## Ground rules
- **No copyrighted books or private data.** Never add manuscripts, corpora, `.docx`/`.epub`
  documents, datasets, or user uploads. Use documents you have the right to share, or keep test
  inputs local (they are gitignored).
- **No secrets.** No API keys, tokens, passwords, `.env` values, private keys, or server details
  (see [SECURITY.md](SECURITY.md)).
- **Preserve evaluator behavior.** Don't change scoring/retrieval semantics without a clear,
  documented reason and matching results.

## Code style
- Python 3.10+; follow the existing style (standard library first, type hints, small focused
  functions, no new heavyweight dependencies without discussion).
- Keep the engine deterministic by default (`hashing_numpy`); don't introduce hidden network or
  model calls.

## Before opening a PR
- Make sure the code imports/compiles:
  ```powershell
  python -m compileall src product_mvp
  ```
- Run the local web app and confirm it starts:
  ```powershell
  python -m uvicorn product_mvp.server_longbook_verifier:app --host 127.0.0.1 --port 8078
  ```
- If you touched the MCP server, confirm it launches over stdio and that any new tool is
  allowlisted and path-checked.
- Describe what you changed and how you verified it. Do not include real data or secrets in the PR.
