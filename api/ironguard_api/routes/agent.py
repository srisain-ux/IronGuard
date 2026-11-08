from fastapi import APIRouter

from ..contracts import example, validate
from ..models import SafetyRequest

router = APIRouter()


@router.post("/v1/agent/safety-card")
def safety_card(payload: SafetyRequest):
    validate("safety_request", payload.model_dump(exclude_none=True))
    card = example("safety_card.bank.json")
    card.update(
        confidence=payload.score["risk"],
        confidence_band=payload.score["confidence_band"],
        entities=payload.entities,
        verdict="caution",
        headline="Demo safety card: pause and verify the sender independently.",
        why=["Safeguard tools are not connected; no contact or domain was verified."],
        checks=[],
        next_steps=[
            {
                "id": "learn",
                "label": "Verify through a known official channel",
                "action": "learn_more",
            }
        ],
        locked_links=payload.entities["urls"] + payload.entities["phones"],
        cool_down=False,
        privacy_note=(
            "Opt-in Photon: forwarded text is held in memory only."
            if payload.source == "photon"
            else "Only entities and the forecast left your device; no message text was sent."
        ),
    )
    return validate("safety_card", card, status=500)
