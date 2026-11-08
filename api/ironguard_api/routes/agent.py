from fastapi import APIRouter, Request

from ..agent.safeguard import HEADLINES, build_card
from ..contracts import validate
from ..events import make_event, scrub_values
from ..models import SafetyRequest

router = APIRouter()


@router.post("/v1/agent/safety-card")
async def safety_card(request: Request, payload: SafetyRequest):
    validate("safety_request", payload.model_dump(exclude_none=True))
    card = await build_card(payload.score, payload.entities, payload.source, payload.text)
    validate("safety_card", card, status=500)
    # The reef dashboard is public: it gets a masked copy, never the user's numbers or links.
    event = scrub_values(card)
    if payload.source == "photon":  # model wording may quote the forwarded thread
        event |= {"headline": HEADLINES[card["verdict"]], "why": [], "next_steps": [
            {"id": s["action"], "label": s["action"].replace("_", " "), "action": s["action"],
             "reply_code": s["reply_code"]} for s in card["next_steps"]]}
    request.app.state.events.publish(make_event("card", event))
    return card
