from anthropic_openai import anthropic_to_sse, openai_chat_to_anthropic, to_openai_chat


def test_tool_schema_and_tool_use_round_trip():
    body = {
        "system": "sys",
        "max_tokens": 32,
        "tools": [
            {
                "name": "Read",
                "description": "read a file",
                "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
            }
        ],
        "messages": [
            {"role": "user", "content": "read x"},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_1",
                        "name": "Read",
                        "input": {"path": "a.py"},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "call_1", "content": "print(1)"}
                ],
            },
        ],
    }
    oai = to_openai_chat(body, model="deepseek/deepseek-v4-pro-0813")
    assert oai["model"] == "deepseek/deepseek-v4-pro-0813"
    assert oai["tools"][0]["function"]["name"] == "Read"
    roles = [m["role"] for m in oai["messages"]]
    assert "tool" in roles
    assert any(m.get("tool_calls") for m in oai["messages"])


def test_openai_tool_calls_become_anthropic_tool_use():
    data = {
        "id": "chat_1",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "Read", "arguments": '{"path":"a.py"}'},
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
    }
    msg = openai_chat_to_anthropic(data, model="deepseek/deepseek-v4-pro-0813")
    assert msg["stop_reason"] == "tool_use"
    assert msg["content"][0]["type"] == "tool_use"
    assert msg["content"][0]["input"]["path"] == "a.py"
    sse = anthropic_to_sse(msg)
    assert "event: message_stop" in sse
    assert "tool_use" in sse
