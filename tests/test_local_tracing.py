import json
import time

from app.utils.tracing import Span, Tracer


def read_trace_file(trace_dir):
    files = list(trace_dir.glob("spans_*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def test_nested_spans_register_under_parent_and_persist_schema(tmp_path):
    tracer = Tracer(trace_dir=tmp_path)

    with Span("Swarm Run", {"objective": "test"}, tracer=tracer) as root:
        time.sleep(0.002)
        with Span("Retrieve Context", {"query": "test"}, tracer=tracer) as child:
            child.set_attribute("chunks", 3)
            time.sleep(0.002)

    assert root.duration_sec > 0
    assert len(root.children) == 1
    assert root.children[0].name == "Retrieve Context"
    assert root.children[0].parent_span_id == root.span_id
    assert root.children[0].trace_id == root.trace_id

    payload = read_trace_file(tmp_path)
    assert payload["trace_id"] == root.trace_id
    assert payload["name"] == "Swarm Run"
    assert payload["status"] == "OK"
    assert payload["attributes"] == {"objective": "test"}
    assert payload["duration_sec"] > 0
    assert len(payload["children"]) == 1
    assert payload["children"][0]["name"] == "Retrieve Context"
    assert payload["children"][0]["attributes"]["chunks"] == 3
    assert payload["children"][0]["status"] == "OK"


def test_span_exception_marks_error_and_preserves_exception(tmp_path):
    tracer = Tracer(trace_dir=tmp_path)

    try:
        with tracer.span("Swarm Run"):
            with tracer.span("Test Execution"):
                raise RuntimeError("verification failed")
    except RuntimeError:
        pass

    payload = read_trace_file(tmp_path)
    child = payload["children"][0]
    assert payload["status"] == "ERROR"
    assert payload["error"]["type"] == "RuntimeError"
    assert child["status"] == "ERROR"
    assert child["error"]["message"] == "verification failed"


def test_execution_time_is_calculated_accurately_enough(tmp_path):
    tracer = Tracer(trace_dir=tmp_path)

    with tracer.span("Timed Work") as span:
        time.sleep(0.02)

    payload = read_trace_file(tmp_path)
    assert span.duration_sec >= 0.015
    assert payload["duration_sec"] >= 0.015
