"""Ephemeral bounded fan-out. Slow subscribers drop old events; no disk or replay."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from .contracts import validate
from .scrub import scrub

router = APIRouter()


class EventBus:
    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()

    @asynccontextmanager
    async def subscribe(self):
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        try:
            yield queue
        finally:
            self.subscribers.discard(queue)

    def publish(self, event):
        validate("event", event)
        for queue in tuple(self.subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)


def make_event(kind, data, job_id=None):
    event = {"type": kind, "ts": datetime.now(UTC).isoformat(), "data": data}
    if job_id is not None:
        event["job_id"] = job_id
    return event


def scrub_values(value):
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, list):
        return [scrub_values(item) for item in value]
    if isinstance(value, dict):
        return {key: scrub_values(item) for key, item in value.items()}
    return value


@router.get("/v1/events")
async def events(request: Request):
    # A connected comment is emitted only after subscriber registration.
    async def stream():
        import json

        async with request.app.state.events.subscribe() as queue:
            yield {"comment": "connected"}
            while True:
                event = await queue.get()
                yield {"event": event["type"], "data": json.dumps(event)}

    return EventSourceResponse(stream(), ping=15)


@router.post("/v1/events/publish", status_code=202)
async def publish(request: Request, payload: dict):
    validate("event", payload)
    # Bridge payloads are untrusted: prevent raw text from reaching the public reef.
    kind = payload["type"]
    if kind == "photon.message":
        preview = payload["data"].get("preview", "")
        if not isinstance(preview, str):
            from fastapi import HTTPException

            raise HTTPException(422, "Invalid preview")
        payload["data"] = {"preview": scrub(preview)[:60]}
    else:
        payload["data"] = scrub_values(payload["data"])
    request.app.state.events.publish(payload)
    return {"accepted": True}
