# Architecture

One evaluation engine, reached three ways locally, plus a separate existing public product.

```mermaid
flowchart LR
  subgraph Local["Local — your machine (no cloud required)"]
    R["User / Researcher"]
    A["Local FastAPI web app<br/>(127.0.0.1:8078)"]
    M["MCP client<br/>(Claude Code / Codex)"]
    S["Local stdio MCP server<br/>(mcp_longbook_server.py)"]
    E["LongBook evaluation engine<br/>(src/: chunk → index → retrieve → eval → claim checks)"]
    O["Reports / results<br/>(outputs/, reports/, product_mvp/runs/)"]

    R --> A
    R --> M --> S
    A --> E
    S --> E
    E --> O
  end

  subgraph Hosted["Existing related public product — NOT required for local use"]
    B["Public browser"] --> U["BookProof UI"] --> API["BookProof API<br/>(public rate-limited demo + token-gated API)"]
  end
```

## Notes
- The **local engine** (`src/`) is self-contained: chunking, deterministic index build
  (`hashing_numpy`), retrieval, the five methods, metrics, and claim verification.
- The **local web app** and the **local stdio MCP server** are two front-ends over that same engine.
  Both run entirely on your machine.
- **BookProof** is an **existing, related public product** (a deployed instance of this evaluation,
  [try it online](https://tts.bedvibe.studio/bookproof/app/)). It is shown here for context only and
  is **not a dependency** of the local stack — nothing in this repository calls it to run locally.
