from server.app import _extract_final, _maybe_parse_tool_call


def test_extract_final_simple():
    text = "Något innan [FINAL]Hej världen![/FINAL] något efter"
    assert _extract_final(text) == "Hej världen!"


def test_extract_final_missing_tags_returns_trimmed():
    text = "Bara text utan taggar"
    assert _extract_final(text) == text


def test_parse_tool_call_with_tag():
    text = "[TOOL_CALL]{\n  \"tool\": \"SET_VOLUME\", \n  \"args\": {\n    \"level\": 30\n  }\n}"
    tc = _maybe_parse_tool_call(text)
    assert isinstance(tc, dict)
    assert tc["tool"] == "SET_VOLUME"
    assert tc["args"]["level"] == 30


def test_parse_tool_call_naked_json():
    text = '{"tool":"PLAY","args":{}}'
    tc = _maybe_parse_tool_call(text)
    assert isinstance(tc, dict)
    assert tc["tool"] == "PLAY"
    assert tc["args"] == {}


