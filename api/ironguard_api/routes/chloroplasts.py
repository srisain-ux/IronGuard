from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/v1/chloroplasts")
def chloroplasts(request: Request):
    return list(request.app.state.chloroplasts.values())


@router.get("/v1/chloroplasts/{id}")
def chloroplast(request: Request, id: str):
    manifest = request.app.state.chloroplasts.get(id)
    if manifest is None:
        raise HTTPException(404, "Unknown chloroplast")
    return manifest
