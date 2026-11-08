from fastapi import APIRouter, Request

from ..contracts import validate
from ..events import make_event
from ..scrub import scrub

router = APIRouter()


@router.post("/v1/reef/report", status_code=202)
async def report(request: Request, payload: dict):
    validate("reef_report", payload)
    # Only retain the re-scrubbed pattern, never the input object.
    clean = {
        **payload,
        "template_text": scrub(payload["template_text"]),
        "family_guess": scrub(payload["family_guess"]),
    }
    request.app.state.reef.append(clean)
    request.app.state.events.publish(
        make_event("reef.report", {"family_guess": clean["family_guess"]})
    )
    return {"accepted": True}
