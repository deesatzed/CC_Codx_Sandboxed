"""Classify OpenRouter (or transport) outcomes as local-fallback or not.

R1 HTTP 401/402/403/408/429/5xx or connect/timeout
R2 error type/code moderation | policy | content_filter
R3 stop_reason / finish_reason in {content_filter, refusal}
R4 text heuristic only if text_heuristic=True (default off)
"""
from __future__ import annotations

from typing import Any

_R1_STATUS = {401, 402, 403, 408, 429}
_STOP = {"content_filter", "refusal"}
_ERR_NEEDLES = ("moderation", "policy", "content_filter", "content-filter")


def is_refusal(
    status: int | None,
    body: dict | None,
    error: BaseException | None,
    *,
    text_heuristic: bool = False,
) -> bool:
    if error is not None:
        return True
    if status is not None and (status in _R1_STATUS or status >= 500):
        return True
    if not isinstance(body, dict):
        return False
    err = body.get("error")
    if isinstance(err, dict):
        blob = f"{err.get('type', '')} {err.get('code', '')} {err.get('message', '')}".lower()
        if any(n in blob for n in _ERR_NEEDLES):
            return True
    if body.get("stop_reason") in _STOP:
        return True
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        finish = choices[0].get("finish_reason") if isinstance(choices[0], dict) else None
        if finish in _STOP:
            return True
    if text_heuristic:
        text = _assistant_text(body).lower()
        if text.startswith("i cannot") or "against my guidelines" in text:
            return True
    return False


def _assistant_text(body: dict) -> str:
    if isinstance(body.get("content"), list):
        return "".join(
            b.get("text", "")
            for b in body["content"]
            if isinstance(b, dict) and b.get("type") == "text"
        )
    choices = body.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        c = msg.get("content")
        return c if isinstance(c, str) else ""
    return ""
