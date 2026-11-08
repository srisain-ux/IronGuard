import asyncio
import sys
import types

import pytest
from fastapi import HTTPException

from ironguard_api.contracts import example, validate
from ironguard_api.events import EventBus, make_event
from ironguard_api.model import load_model
from ironguard_api.scrub import scrub


@pytest.mark.parametrize(
    "schema,value",
    [
        ("score_request", {"turns": []}),
        ("score_response", {"risk": 1.1}),
        ("reef_report", {**example("reef_report.photon.json"), "consent": False}),
        ("event", {"type": "score", "ts": "not-a-date", "data": {}}),
    ],
)
def test_validator_rejects_without_echoing_input(schema, value):
    with pytest.raises(HTTPException) as caught:
        validate(schema, value)
    assert caught.value.status_code == 422
    assert caught.value.detail == f"Invalid {schema} payload"


@pytest.mark.parametrize(
    "text,placeholder",
    [
        ("+1 (214) 555-0123", "[PHONE]"),
        ("a@example.com", "[EMAIL]"),
        ("https://evil.example/pay", "[URL]"),
        ("evil.example/pay", "[URL]"),
        ("$45.50", "[AMOUNT]"),
        ("$12345678", "[AMOUNT]"),
        ("50 dollars", "[AMOUNT]"),
        ("@username", "[NAME]"),
        ("Anna", "[NAME]"),
        ("PNC", "[BRAND]"),
    ],
)
def test_scrubber(text, placeholder):
    assert scrub(text) == placeholder
    assert scrub(placeholder) == placeholder


def test_rejections_and_privacy(client, app):
    assert client.post("/v1/score", json={"turns": []}).status_code == 422
    assert client.post("/v1/score", json={"turns": [], "secret": "private"}).status_code == 422
    score = example("score_response.turn3.json")
    request = {"score": score, "entities": {"brands": [], "phones": [], "urls": []}}
    assert (
        client.post("/v1/agent/safety-card", json={**request, "text": "private"}).status_code == 422
    )
    assert client.post("/v1/agent/safety-card", json={**request, "entities": {}}).status_code == 422
    assert (
        client.post(
            "/v1/agent/safety-card", json={**request, "source": "photon", "text": "private"}
        ).status_code
        == 200
    )
    assert client.post("/v1/zero-day", json={"alert": " "}).status_code == 422
    report = example("reef_report.photon.json")
    assert client.post("/v1/reef/report", json={**report, "consent": False}).status_code == 422
    assert not app.state.reef
    report["template_text"] = "Anna call +1-214-555-0123 at a@example.com pay $45 to PNC"
    assert client.post("/v1/reef/report", json=report).status_code == 202
    assert app.state.reef[0]["template_text"] == (
        "[NAME] call [PHONE] at [EMAIL] pay [AMOUNT] to [BRAND]"
    )
    assert client.get("/v1/chloroplasts/../../.env").status_code == 404
    assert client.get("/v1/chloroplasts/cp_missing").status_code == 404
    assert client.post("/v1/events/publish", json={"type": "unknown"}).status_code == 422


def test_cors(client):
    response = client.options(
        "/v1/score",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options(
        "/v1/score",
        headers={
            "Origin": "https://other.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_bounded_fanout_cleanup_and_bridge_scrubbing(client, app):
    async def exercise():
        async with app.state.events.subscribe() as first, app.state.events.subscribe() as second:
            for step in range(105):
                app.state.events.publish(make_event("train.progress", {"step": step}))
            assert first.qsize() == second.qsize() == 100
            assert (await first.get())["data"]["step"] == 5
        assert not app.state.events.subscribers

    asyncio.run(exercise())
    assert isinstance(app.state.events, EventBus)


def test_model_delegation(monkeypatch, tmp_path):
    expected = object()
    fake = types.ModuleType("ironguard_ml.stub")
    fake.load = lambda artifacts: expected
    monkeypatch.setitem(sys.modules, "ironguard_ml.stub", fake)
    assert load_model("stub", tmp_path) is expected
    with pytest.raises(RuntimeError):
        load_model("invalid", tmp_path)


def test_bridge_preview_scrubbed_and_bounded(client, app):
    queue = asyncio.Queue()
    app.state.events.subscribers.add(queue)
    event = make_event(
        "photon.message",
        {
            "preview": "Anna a@example.com $45 " + "x" * 100,
            "text": "Never broadcast this field",
        },
    )
    assert client.post("/v1/events/publish", json=event).status_code == 202
    result = queue.get_nowait()
    assert set(result["data"]) == {"preview"}
    preview = result["data"]["preview"]
    assert preview.startswith("[NAME] [EMAIL] [AMOUNT]")
    assert len(preview) <= 60
    app.state.events.subscribers.clear()


def test_zero_day_background_reports_demo_limitation(client, app):
    queue = asyncio.Queue()
    app.state.events.subscribers.add(queue)
    response = client.post("/v1/zero-day", json={"alert": "Parking payment pretext"})
    event = queue.get_nowait()
    assert event["type"] == "error"
    assert event["job_id"] == response.json()["job_id"]
    assert "not connected" in event["data"]["message"]
    app.state.events.subscribers.clear()


def test_store_manifests_loaded_and_model_loaded_once(monkeypatch, tmp_path):
    import json

    from fastapi.testclient import TestClient

    from ironguard_api import main
    from ironguard_api.model import FixtureModel

    calls = []
    monkeypatch.setattr(main, "load_model", lambda *args: calls.append(args) or FixtureModel())
    monkeypatch.setenv("IRONGUARD_MODEL", "stub")
    manifest = example("chloroplast.parking.json")
    manifest["id"] = "cp_saved_demo"
    (tmp_path / "saved.json").write_text(json.dumps(manifest))
    with TestClient(main.create_app(store=tmp_path)) as client:
        assert client.get("/v1/chloroplasts/cp_saved_demo").json() == manifest
        for _ in range(2):
            assert (
                client.post("/v1/score", json=example("score_request.photon.json")).status_code
                == 200
            )
    assert len(calls) == 1
