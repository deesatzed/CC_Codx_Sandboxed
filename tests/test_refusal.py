from refusal import classify_refusal, is_refusal


def test_http_429_is_refusal():
    assert is_refusal(429, None, None) is True


def test_http_200_ok_is_not_refusal():
    body = {
        "choices": [
            {"finish_reason": "stop", "message": {"role": "assistant", "content": "ping"}}
        ]
    }
    assert is_refusal(200, body, None) is False


def test_content_filter_finish_reason_is_refusal():
    body = {
        "choices": [
            {
                "finish_reason": "content_filter",
                "message": {"role": "assistant", "content": ""},
            }
        ]
    }
    assert is_refusal(200, body, None) is True


def test_anthropic_stop_reason_refusal():
    body = {"stop_reason": "refusal", "content": [{"type": "text", "text": "no"}]}
    assert is_refusal(200, body, None) is True


def test_error_body_moderation_is_refusal():
    body = {"error": {"type": "moderation", "message": "blocked"}}
    assert is_refusal(200, body, None) is True


def test_transport_error_is_refusal():
    assert is_refusal(None, None, OSError("connection refused")) is True


def test_classify_codes_match_is_refusal():
    assert classify_refusal(429, None, None) == "R1"
    assert is_refusal(429, None, None) is True
    assert classify_refusal(200, {"choices": [{"finish_reason": "stop"}]}, None) is None


def test_text_heuristic_off_does_not_trip_on_i_cannot():
    body = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "I cannot help with that."},
            }
        ]
    }
    assert is_refusal(200, body, None, text_heuristic=False) is False
