"""Zero-day job and reef persistence: fake Nemotron, contract-checked trainer, real SSE bus."""

import asyncio
import hashlib
import itertools
import json
from functools import partial

import pytest

from ironguard_api.agent import nemotron
from ironguard_api.agent import zero_day as pipeline
from ironguard_api.contracts import example, validator

AXES = {a: [f"{a} one", f"{a} two"] for a in pipeline.AXES}
words = itertools.count()


def conv(hard):
    def turn(sender, stage, i):
        return {"sender": sender, "stage": stage, "text": f"msg {next(words)} qx{i} zv{next(words)} ok"}

    stages = ["benign"] * 4 if hard else ["bait", "bait", "strike", "strike"]
    return {"channel": "sms", "turns": [turn("them" if i % 2 == 0 else "me", s, i) for i, s in enumerate(stages)]}


async def fake_chat_json(messages, **kwargs):
    prompt = messages[0]["content"]
    if prompt.startswith("You design variations"):
        return {"family_id": "zd_test_family", "label": "Test family", "axes": AXES}
    if prompt.startswith("You review"):
        n = len(json.loads(prompt.split("Conversations: ", 1)[1]))
        return {"scores": [{"i": i, "realism": 5, "label_correct": True} for i in range(n)]}
    return {"conversations": [conv('Family: benign' in prompt) for _ in range(5)]}


@pytest.fixture
def events(app, monkeypatch):
    monkeypatch.setenv("NEMOTRON_GEN_MODEL", "g")
    monkeypatch.setenv("NEMOTRON_AGENT_MODEL", "a")
    queue = asyncio.Queue()
    app.state.events.subscribers.add(queue)
    yield lambda: [queue.get_nowait() for _ in range(queue.qsize())]
    app.state.events.subscribers.clear()


@pytest.mark.parametrize("real_trainer", [False, True])
def test_job_end_to_end(client, app, events, monkeypatch, real_trainer):
    from ironguard_ml.stub import train

    if real_trainer:
        np = pytest.importorskip("numpy")
        torch = pytest.importorskip("torch")
        chloroplast = pytest.importorskip("ironguard_ml.chloroplast")
        from ironguard_ml.data import _parse
        from ironguard_ml.preynet import PreyNet

        def encoder(texts):
            return np.stack([np.random.default_rng(int(hashlib.sha256(t.encode()).hexdigest()[:8], 16))
                             .normal(size=384) for t in texts])

        with torch.random.fork_rng():
            torch.manual_seed(0)
            net = PreyNet().eval()
        pool = [_parse({**conv(True), "id": f"bank_{i}", "family": "benign", "strike_turn": None,
                        "source": {"generator": "nemotron"}}, "bank") for i in range(30)]
        base = chloroplast.Base(net, *chloroplast.conversation_features(net, pool, encoder), encoder=encoder)
        train = partial(chloroplast.train, base=base)

    def checked_train(**kwargs):
        records = kwargs["pos"] + kwargs["neg"]
        for record in records:
            validator("conversation").validate(record)
        assert len({record["id"] for record in records}) == len(records)
        return train(**kwargs)

    monkeypatch.setattr(pipeline, "trainer", lambda: checked_train)
    monkeypatch.setattr(nemotron, "chat_json", fake_chat_json)
    response = client.post("/v1/zero-day", json={"alert": "Fake parking boot fee", "n_pos": 10, "n_neg": 10})
    assert response.status_code == 202 and response.json()["status"] == "queued"
    got = events()
    kinds = [e["type"] for e in got]
    assert {e["job_id"] for e in got} == {response.json()["job_id"]}
    assert {e["data"]["stage"] for e in got if e["type"] == "algae.progress"} == {
        "plan", "generate", "critique", "dedupe"}
    assert kinds.index("train.progress") < kinds.index("chloroplast.ready") == len(kinds) - 1
    ready = got[-1]["data"]
    assert "weights" not in ready and ready["family_id"] == "zd_test_family"
    assert (ready["metrics"]["n_pos"], ready["metrics"]["n_neg"]) == (10, 10)
    stored = json.loads((app.state.chloroplast_dir / f"{ready['id']}.json").read_text())
    validator("chloroplast").validate(stored)
    assert client.get(f"/v1/chloroplasts/{ready['id']}").json() == stored
    assert not app.state.jobs


def test_job_failure_is_an_error_event(client, app, events, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("private detail")

    monkeypatch.setattr(nemotron, "chat_json", broken)
    client.post("/v1/zero-day", json={"alert": "Fake parking boot fee"})
    (event,) = events()
    assert event["type"] == "error" and "RuntimeError" in event["data"]["message"]
    assert "private" not in event["data"]["message"] and not app.state.jobs


def test_too_few_conversations_is_not_trained(client, events, monkeypatch):
    async def critic_rejects(messages, **kwargs):
        out = await fake_chat_json(messages, **kwargs)
        for s in out.get("scores", []):
            s["realism"] = 1
        return out

    monkeypatch.setattr(nemotron, "chat_json", critic_rejects)
    client.post("/v1/zero-day", json={"alert": "Fake parking boot fee", "n_pos": 10, "n_neg": 10})
    last = events()[-1]
    assert last["type"] == "error" and "not training" in last["data"]["message"]


def test_request_limits_and_job_cap(client, app):
    for body in ({"alert": "x", "n_pos": 9}, {"alert": "x", "n_neg": 301}, {"alert": "x", "n": 5}):
        assert client.post("/v1/zero-day", json=body).status_code == 422
    app.state.jobs.update({"a", "b"})
    assert client.post("/v1/zero-day", json={"alert": "x"}).status_code == 429


def test_parse_plan_rejects_bad_axes_and_ids():
    family, label, axes = pipeline.parse_plan(
        {"family_id": "../evil", "label": 5, "axes": {a: [" v ", 3] for a in pipeline.AXES}}, "alert")
    assert family.startswith("zd_") and label == "alert" and axes["pretext"] == ["v"]
    with pytest.raises(pipeline.JobError):
        pipeline.parse_plan({"axes": {"pretext": ["a"]}}, "alert")


def test_reef_report_persisted_scrubbed(client, app):
    report = example("reef_report.photon.json")
    report["template_text"] = "Anna call +1-214-555-0123 pay $45"
    report["family_guess"] = "x" * 500
    assert client.post("/v1/reef/report", json=report).status_code == 202
    (line,) = app.state.reef_path.read_text().splitlines()
    saved = json.loads(line)
    assert saved["template_text"] == "[NAME] call [PHONE] pay [AMOUNT]" and len(saved["family_guess"]) == 80
    assert client.post("/v1/reef/report", json={**report, "consent": False}).status_code == 422
    assert len(app.state.reef_path.read_text().splitlines()) == 1


def test_dead_endpoint_fails_fast(client, events, monkeypatch):
    async def plan_only(messages, **kwargs):
        if messages[0]["content"].startswith("You design variations"):
            return await fake_chat_json(messages, **kwargs)
        raise ValueError("down")

    monkeypatch.setattr(nemotron, "chat_json", plan_only)
    client.post("/v1/zero-day", json={"alert": "Fake parking boot fee", "n_pos": 10, "n_neg": 10})
    assert events()[-1]["data"]["message"] == "Every Nemotron call failed (ValueError)"
