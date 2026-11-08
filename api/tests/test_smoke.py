"""All public routes, contract validation, and a real HTTP SSE round trip."""

import json
import socket
import threading
import time

import httpx
import uvicorn

from ironguard_api.contracts import example, validator


def check(response, schema, status=200):
    assert response.status_code == status, response.text
    validator(schema).validate(response.json())
    return response.json()


def test_every_json_route(client):
    check(client.get("/health"), "health")
    score = check(
        client.post("/v1/score", json=example("score_request.photon.json")), "score_response"
    )
    card = check(
        client.post(
            "/v1/agent/safety-card",
            json={
                "score": score,
                "entities": {"brands": ["PNC"], "phones": [], "urls": []},
            },
        ),
        "safety_card",
    )
    assert card["confidence"] == score["risk"]
    # Only real tool runs appear as checks (here: the offline directory lookup).
    assert [c["tool"] for c in card["checks"]] == ["lookup_official_contact"]
    check(
        client.post("/v1/zero-day", json={"alert": "Fake parking boot payment"}),
        "zero_day_response",
        202,
    )
    manifests = check(client.get("/v1/chloroplasts"), "chloroplast_list")
    check(client.get(f"/v1/chloroplasts/{manifests[0]['id']}"), "chloroplast")
    check(client.post("/v1/reef/report", json=example("reef_report.photon.json")), "accepted", 202)
    check(
        client.post("/v1/events/publish", json=example("event.train_progress.json")),
        "accepted",
        202,
    )
    check(client.get("/v1/metrics"), "metrics")
    check(client.get("/models/preynet.onnx"), "error", 404)


def test_artifact_routes_serve_real_files(client, app):
    metrics = {"models": {"PreyNet": {"lead_time": 1.25}}}
    (app.state.artifacts / "eval_summary.json").write_text(json.dumps(metrics))
    assert check(client.get("/v1/metrics"), "metrics") == metrics
    content = b"artifact-fixture-only"
    (app.state.artifacts / "preynet.onnx").write_bytes(content)
    response = client.get("/models/preynet.onnx")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.content == content


def test_sse_round_trip_and_disconnect(app):
    # TestClient buffers infinite responses; use an ephemeral local HTTP listener.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with (
                httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5) as client,
                client.stream("GET", "/v1/events") as response,
            ):
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                lines = response.iter_lines()
                assert next(lines) == ": connected"
                event = example("event.train_progress.json")
                check(client.post("/v1/events/publish", json=event), "accepted", 202)
                for line in lines:
                    if line.startswith("data: "):
                        result = json.loads(line[6:])
                        validator("event").validate(result)
                        assert result == event
                        break
                else:
                    raise AssertionError("No event received")
            deadline = time.monotonic() + 5
            while app.state.events.subscribers and time.monotonic() < deadline:
                time.sleep(0.01)
            assert not app.state.events.subscribers
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive()
