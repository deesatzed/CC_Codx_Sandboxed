from responses_bridge import (
    compress_responses_for_local,
    extract_output_text,
    responses_to_sse,
    wrap_chat_as_response,
)


def test_compress_sets_local_model_and_short_instructions():
    body = {
        "model": "deepseek/deepseek-v4-pro-0813",
        "instructions": "X" * 5000,
        "input": "hi",
        "stream": True,
    }
    out = compress_responses_for_local(body, local_model="/abs/model")
    assert out["model"] == "/abs/model"
    assert len(out.get("instructions") or "") < 800
    assert out["input"] == "hi"


def test_wrap_chat_as_response_has_output_text():
    chat = {
        "id": "chat_1",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "ping"},
            }
        ],
    }
    resp = wrap_chat_as_response(chat, model="local")
    assert resp["object"] == "response"
    assert extract_output_text(resp) == "ping"
    sse = responses_to_sse(resp)
    assert "response.completed" in sse
    assert "ping" in sse
