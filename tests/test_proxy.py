from proxy import flatten_content, openai_resp_to_anthropic, to_openai_messages


def test_flatten_string():
    assert flatten_content("hello") == "hello"


def test_flatten_blocks():
    assert flatten_content([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]) == "ab"


def test_to_openai_messages_includes_system():
    body = {
        "system": "sys",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
    }
    assert to_openai_messages(body) == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]


def test_openai_resp_to_anthropic_shape():
    out = openai_resp_to_anthropic(
        {
            "id": "x",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        },
        "local-model",
    )
    assert out["role"] == "assistant"
    assert out["content"][0]["text"] == "ok"
    assert out["usage"]["output_tokens"] == 2
