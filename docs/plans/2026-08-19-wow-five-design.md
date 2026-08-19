# Five wow receipts — design

Date: 2026-08-19  
Status: implementing  
Workspace: this sandbox (CC_Codx_Sandboxed)

## What this is

Five user-approved enhancements. Each is a **receipt**, not a slogan. No mocked hops, no fake denies.

| # | Name | Receipt |
|---|---|---|
| 1 | Hop tape | `receipts/hops.jsonl` + `./doctor-receipt.sh` |
| 2 | Sandbox tape | `./prove-sandbox.sh` |
| 3 | Graph-first | inject `graphify-out/graph.json` into local shorthand; agent rules |
| 4 | Witness log | `witness.jsonl` from launch + tool hooks |
| 5 | `$local` / `/local` | `.force-local` consumed on the next hop |

## Rules

- Refusal corpus lines are written only when OpenRouter actually refused (R1–R4) and local ran.
- `doctor-receipt` hop B uses a **real** TCP connect to a closed loopback port (R1), then a **real** mlx hop if `:8080` is up.
- `prove-sandbox` reports what Safehouse actually does. Default Safehouse **allows** `/tmp` and outbound TCP; those are not claimed as denies.
- If `graphify-out/graph.json` is missing, graph inject is a no-op (not a fake graph).

## Non-goals

Pi/RAG, GC-A2A wiring, starting extra mlx/router processes, committing `.env` or hop logs.
