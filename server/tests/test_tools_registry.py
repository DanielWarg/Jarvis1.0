from server.tools.registry import validate_and_execute_tool


def test_set_volume_requires_level_or_delta():
    res = validate_and_execute_tool("SET_VOLUME", {})
    assert res["ok"] is False
    assert res.get("error") == "invalid_args"


def test_set_volume_level_valid():
    res = validate_and_execute_tool("SET_VOLUME", {"level": 30})
    assert res["ok"] is True
    assert res["result"]["level"] == 30


def test_set_volume_delta_valid():
    res = validate_and_execute_tool("SET_VOLUME", {"delta": -10})
    assert res["ok"] is True
    assert res["result"]["delta"] == -10


def test_play_pause_ok():
    r1 = validate_and_execute_tool("PLAY", {})
    r2 = validate_and_execute_tool("PAUSE", {})
    assert r1["ok"] is True and r1["tool"] == "PLAY"
    assert r2["ok"] is True and r2["tool"] == "PAUSE"


def test_unknown_tool():
    res = validate_and_execute_tool("NOPE", {})
    assert res["ok"] is False
    assert res.get("error") == "unknown_tool"


