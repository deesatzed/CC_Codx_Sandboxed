import json
from pathlib import Path

from witness import append_witness


def test_append_witness_is_append_only(tmp_path: Path):
    append_witness(tmp_path, host="claude", event="session_start", path=".")
    append_witness(
        tmp_path,
        host="claude",
        event="tool",
        tool="Bash",
        path="ls",
    )
    lines = (tmp_path / "witness.jsonl").read_text().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["event"] == "session_start"
    assert second["tool"] == "Bash"
    assert second["host"] == "claude"
