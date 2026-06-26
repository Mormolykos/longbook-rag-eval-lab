# Limitations

- This is a pilot plus extended stress-test benchmark, not a universal model ranking and not a state of the art claim.
- Term-overlap scoring is lightweight and is not full semantic correctness.
- QID parsing and fallback parsing may vary by Markdown format.
- The private corpus limits public reproducibility unless a public-domain parallel corpus is added.
- Model interfaces, quotas, and file-access behavior differ across systems and may change over time.
- Free-tier consumer protocol and enhanced-access reference protocol results should not be merged into a single leaderboard.
- Enhanced Claude Code and ChatGPT Plus runs are not included in the free-tier ranking.
- A non-completion note exists at `data/systems_mirelands5/sonnet_claude_ai_free_failed_output.md`; it records that Claude.ai free-tier Sonnet 4.6 did not complete the 80-question evaluation under continuation/quota limits after three free-account attempts, and is not included in the answer-quality ranking.
