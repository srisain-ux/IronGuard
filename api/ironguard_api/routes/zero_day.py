import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..agent import zero_day as pipeline
from ..events import make_event
from ..models import ZeroDayRequest

router = APIRouter()
JOB_TIMEOUT = 1800  # seconds
MAX_JOBS = 2  # each job holds Nemotron busy for minutes; the endpoint is unauthenticated


async def run(app, job_id, payload: ZeroDayRequest):
    state = app.state

    def emit(kind, data):
        state.events.publish(make_event(kind, data, job_id))

    try:
        async with asyncio.timeout(JOB_TIMEOUT):
            manifest = await pipeline.run_job(
                emit, payload.alert, payload.n_pos, payload.n_neg, state.chloroplast_dir
            )
        state.chloroplasts[manifest["id"]] = manifest
        emit("chloroplast.ready", {k: v for k, v in manifest.items() if k != "weights"})
    except pipeline.JobError as exc:
        emit("error", {"message": str(exc)})
    except Exception as exc:
        logging.getLogger(__name__).exception("zero-day job failed")
        emit("error", {"message": f"Zero-day job failed ({type(exc).__name__})"})
    finally:
        state.jobs.discard(job_id)


@router.post("/v1/zero-day", status_code=202)
async def zero_day(payload: ZeroDayRequest, request: Request, tasks: BackgroundTasks):
    if len(request.app.state.jobs) >= MAX_JOBS:
        raise HTTPException(429, "Too many zero-day jobs running")
    job_id = "zd_" + uuid4().hex
    request.app.state.jobs.add(job_id)
    tasks.add_task(run, request.app, job_id, payload)
    return {"job_id": job_id, "status": "queued", "events_url": "/v1/events"}
