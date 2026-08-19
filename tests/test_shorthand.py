from shorthand import compress_for_local


def test_replaces_system_and_collapses_tools():
    fat_schema = {"type": "object", "properties": {f"k{i}": {"type": "string"} for i in range(80)}}
    body = {
        "model": "opus",
        "system": "x" * 8000,
        "tools": [
            {
                "name": "Read",
                "description": "Read a file from disk",
                "input_schema": fat_schema,
            }
        ],
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1024,
    }
    out = compress_for_local(body, local_model="/abs/model")
    assert out["model"] == "/abs/model"
    assert len(str(out.get("system", ""))) < 2000
    assert out["system"] != body["system"]
    assert "coding agent" in str(out.get("system", "")).lower()
    tool = out["tools"][0]
    assert tool["name"] == "Read"
    assert json_size(tool) < json_size(body["tools"][0])


def test_truncates_huge_tool_result():
    huge = "A" * 20000
    body = {
        "system": "sys",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "1", "content": huge}
                ],
            }
        ],
    }
    out = compress_for_local(body, local_model="/m")
    text = _flatten(out["messages"][0]["content"])
    assert len(text) < 8000
    assert "truncated" in text.lower()


def json_size(obj) -> int:
    import json

    return len(json.dumps(obj))


def _flatten(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("content", block.get("text", ""))))
        return "".join(parts)
    return str(content)
