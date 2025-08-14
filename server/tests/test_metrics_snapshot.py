from server.metrics import metrics


def test_metrics_snapshot_shape():
    metrics.reset()
    metrics.record_first_token(100)
    metrics.record_final_latency(250)
    metrics.record_tool_call_attempted()
    metrics.record_tool_validation_failed()
    metrics.record_tool_call_latency(80)
    metrics.record_router_hit()
    metrics.record_llm_hit()
    snap = metrics.snapshot()
    assert "first_token_ms" in snap and "final_latency_ms" in snap
    assert snap["counters"]["tool_calls_attempted"] == 1
    assert snap["counters"]["tool_validation_failed"] == 1
    assert snap["counters"]["router_hits"] == 1
    assert snap["counters"]["llm_hits"] == 1


