import json

from fastapi import APIRouter, HTTPException, Request

from ..contracts import validate
from ..events import make_event
from ..scrub import scrub

router = APIRouter()
MAX_BYTES = 5_000_000  # shortcut: the queue file only stops growing; rotate or move to a DB if the reef outlives the demo


@router.post("/v1/reef/report", status_code=202)
async def report(request: Request, payload: dict):
    validate("reef_report", payload)
    # Only retain the re-scrubbed pattern, never the input object.
    clean = {
        **payload,
        "template_text": scrub(payload["template_text"]),
        "family_guess": scrub(payload["family_guess"])[:80],
    }
    path = request.app.state.reef_path
    if path.exists() and path.stat().st_size >= MAX_BYTES:
        raise HTTPException(503, "Reef queue is full")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(clean) + "\n")
    request.app.state.reef.append(clean)
    request.app.state.events.publish(
        make_event("reef.report", {"family_guess": clean["family_guess"]})
    )
    return {"accepted": True}
