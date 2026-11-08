from fastapi import APIRouter, HTTPException, Request

from ..contracts import validate

router = APIRouter()


@router.post("/v1/score")
def score(request: Request, payload: dict):
    validate("score_request", payload)
    ids = payload.get("chloroplast_ids")
    manifests = request.app.state.chloroplasts
    if ids is not None and any(item not in manifests for item in ids):
        raise HTTPException(404, "Unknown chloroplast")
    selected = list(manifests.values()) if ids is None else [manifests[item] for item in ids]
    # Fixture weights are examples, not deployable heads.
    if request.app.state.mode == "stub":
        selected = []
    response = request.app.state.model.score(turns=payload["turns"], chloroplasts=selected)
    return validate("score_response", response, status=500)
