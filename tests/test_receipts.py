from pathlib import Path

from receipts import consume_force_local, write_hop, write_refusal_if_real
from refusal import classify_refusal


def test_classify_r1_transport():
    assert classify_refusal(None, None, OSError("refused")) == "R1"


def test_classify_r1_status():
    assert classify_refusal(429, {}, None) == "R1"


def test_classify_r2_moderation():
    assert classify_refusal(200, {"error": {"type": "moderation"}}, None) == "R2"


def test_classify_r3_finish():
    body = {"choices": [{"finish_reason": "content_filter", "message": {}}]}
    assert classify_refusal(200, body, None) == "R3"


def test_classify_ok():
    body = {"choices": [{"finish_reason": "stop", "message": {"content": "ping"}}]}
    assert classify_refusal(200, body, None) is None


def test_write_hop_and_refusal_corpus(tmp_path: Path):
    hop = write_hop(
        tmp_path,
        via="local",
        reason="R1",
        route="/v1/messages",
        or_status=None,
        err="ConnectError",
        usage={"prompt_tokens": 3},
        or_excerpt="connection refused",
        local_excerpt="pong",
    )
    hops = (tmp_path / "receipts" / "hops.jsonl").read_text().strip().splitlines()
    assert len(hops) == 1
    assert '"via": "local"' in hops[0]
    assert '"reason": "R1"' in hops[0]
    write_refusal_if_real(tmp_path, hop)
    corpus = (tmp_path / "receipts" / "refusals.jsonl").read_text()
    assert "connection refused" in corpus
    assert "pong" in corpus


def test_ok_hop_does_not_write_refusal_corpus(tmp_path: Path):
    hop = write_hop(tmp_path, via="openrouter", reason="ok", route="/v1/messages")
    write_refusal_if_real(tmp_path, hop)
    assert not (tmp_path / "receipts" / "refusals.jsonl").is_file()


def test_consume_force_local(tmp_path: Path):
    flag = tmp_path / ".force-local"
    flag.write_text("1\n")
    assert consume_force_local(tmp_path) is True
    assert not flag.exists()
    assert consume_force_local(tmp_path) is False
