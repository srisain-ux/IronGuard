import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/health")
def health(request: Request):
    return {"status": "ok", "model": request.app.state.mode, "fixture": request.app.state.fixture}


@router.get("/v1/metrics")
def metrics(request: Request):
    path = request.app.state.artifacts / "eval_summary.json"
    if not path.is_file():
        return {"available": False, "models": {}, "display": "--"}
    return json.loads(path.read_text())


@router.get("/models/preynet.onnx")
def onnx(request: Request):
    path = request.app.state.artifacts / "preynet.onnx"
    if not path.is_file():
        raise HTTPException(404, "PreyNet ONNX artifact is not available")
    return FileResponse(path, media_type="application/octet-stream", filename="preynet.onnx")
