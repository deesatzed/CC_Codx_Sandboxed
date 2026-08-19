---
description: Pin the next model hop to local Abliterated 4bit (hybrid router .force-local)
---

# /local  (Codex: $local)

Pin **only the next** hybrid-router hop to the local Abliterated 4bit. This is not a mock. The router consumes `.force-local` and skips OpenRouter for that one request.

Do this, then continue the user's task:

```bash
printf '1\n' > .force-local
```

Tell the user: the following model call will be `via=local reason=force-local` in `receipts/hops.jsonl`. If mlx is not running, that hop will fail honestly.

Do not invent a local answer without the router hop.
