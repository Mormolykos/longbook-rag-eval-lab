# Security Policy

## No production credentials in this repository
This repository contains **no** API keys, tokens, passwords, private keys, server IPs, or
production credentials. The BookProof token-gated API is authenticated by a secret that is supplied
only via the server environment and is **never** committed here.

## Never commit secrets
Do not add API keys, tokens, passwords, `.env` files with values, private keys, or real
server/host details to this repository. The `.gitignore` excludes common secret and environment
files, but treat that as a backstop, not a guarantee — review your diffs.

## Reporting a vulnerability
**Please do not report security issues in public** (no public issues, discussions, or pull
requests describing the vulnerability).

Report privately via **[GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)**
on this repository (the "Security" tab → "Report a vulnerability"). Please include reproduction
steps and affected files. No email contact is published; use Security Advisories only.

## Scope
This project runs **locally**: a FastAPI web app on `127.0.0.1` and a local stdio MCP server. The
MCP server uses an allowlisted set of local scripts, strict read/write path checks, and makes no
external/cloud calls (see the Security model in [README.md](README.md)).
