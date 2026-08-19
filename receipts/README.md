# Receipts

`hops.jsonl` and `refusals.jsonl` are written by the hybrid router. They are gitignored.

- `hops.jsonl` — every `/v1/messages` and `/v1/responses` hop (`via`, `reason`, tokens).
- `refusals.jsonl` — only when OpenRouter actually refused (R1–R4) and local ran.

`./doctor-receipt.sh` appends a live OpenRouter hop plus a real closed-port R1.
