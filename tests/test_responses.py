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
    assert "response.output_item.added" in sse
    assert "response.output_text.delta" in sse
    assert "response.completed" in sse
    assert "ping" in sse
    assert sse.find("response.output_item.added") < sse.find("response.output_text.delta")


def test_sse_replays_function_call_items():
    resp = {
        "id": "resp_tools",
        "object": "response",
        "status": "completed",
        "model": "deepseek/deepseek-v4-pro-0813",
        "output": [
            {
                "id": "fc_1",
                "type": "function_call",
                "name": "exec",
                "call_id": "call_1",
                "arguments": '{"cmd":"pwd"}',
            }
        ],
    }
    sse = responses_to_sse(resp)
    assert "response.output_item.added" in sse
    assert '"name": "exec"' in sse
    assert "function_call_arguments.done" in sse
    assert sse.find("response.output_item.added") < sse.find("function_call_arguments.done")
    assert sse.find("function_call_arguments.done") < sse.find("response.completed")
