# BUILD checklist — claude-mlx-sandbox

Do these in order. Do not skip. Do not start the 27B server until step 5.

## 0. Facts (do not “fix” these)

- Weights are MLX, not GGUF. llamafile will not load them.
- Default model (user-selected): `PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit`
- Loader: q38Ablit `.venv` `mlx_vlm.server` (same family as `cli-chat.py`)
- This directory is the Safehouse workdir. Parent repo `qwentient64` must not receive these files (nested git + parent gitignore).
- No Pi, no RAG, no GC-A2A in this build.

## 1. Files exist

- [ ] `paths.sh`, `setup.sh`, `check.sh`, `run-mlx.sh`, `run-claude.sh`, `run-proxy.sh`, `proxy.py`
- [ ] `tests/test_model_path.py`, `tests/test_proxy.py`

## 2. Unit tests (no 27B load)

```bash
cd /Volumes/WS4TB/q38Ablit/claude-mlx-sandbox
/Volumes/WS4TB/q38Ablit/.venv/bin/python -m pytest tests/ -q
```

Pass: all tests green.

## 3. Install Safehouse only if missing

```bash
./setup.sh
```

Must not pip into Homebrew 3.14. Must not download weights.
If `brew install eugene1g/safehouse/agent-safehouse` fails on Xcode, `setup.sh` installs the upstream standalone `safehouse.sh` into `~/.local/bin`.

## 4. Offline check

```bash
./check.sh
```

Pass: prints `check passed (no 27B load)`.

## 4b. Hybrid router (OpenRouter first)

- [ ] Copy `.env.example` → `.env`
- [ ] Set `OPENROUTER_API_KEY` (you paste it; this repo does not copy keys)
- [ ] Confirm `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813`
- [ ] `./run-router.sh` (Terminal 2) then `./run-claude.sh` (Terminal 3)
- [ ] Keep `./run-mlx.sh` for refusal fallback

## 5. Live server (explicit; spends RAM on the 27B 4bit)

Terminal 1:

```bash
./run-mlx.sh
```

Wait until:

```bash
curl -sf http://127.0.0.1:8080/health
```

returns ok.

## 6. Claude inside Safehouse

Terminal 2:

```bash
./run-claude.sh
```

Then: `./prove-sandbox.sh` (workdir write must pass; parent write must fail). Do not assume `/tmp` is denied — default Safehouse often allows it; the script reports the truth.

## 7. Receipts (router must be running; restart router after this pull)

```bash
./doctor-receipt.sh
```

Pass: hop B `reason=R1` with a real closed-port error. Local mlx `local_ok` only if `./run-mlx.sh` is up.

`/local` or `$local` writes `.force-local` for the next hop.

## 8. Fallback only if step 6 cannot talk Anthropic

Terminal extra: `./run-proxy.sh`  
Then: `USE_PROXY=1 ./run-claude.sh`

## Out of checklist (needs approval)

- Switching to OptiQ-4bit
- Adding PiRag / LFM2.5
- Changing `--host` off 127.0.0.1
- Using `--dangerously-skip-permissions` without Safehouse
