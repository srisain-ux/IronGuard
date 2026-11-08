from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request

from ..events import make_event
from ..models import ZeroDayRequest

router = APIRouter()


async def run_demo_job(app, job_id):
    # No synthetic training claims or fake progress: the full pipeline is a later task.
    app.state.events.publish(
        make_event(
            "error",
            {"message": "Demo only: Algae generation and adapter training are not connected."},
            job_id,
        )
    )


@router.post("/v1/zero-day", status_code=202)
def zero_day(payload: ZeroDayRequest, request: Request, tasks: BackgroundTasks):
    job_id = "zd_" + uuid4().hex
    tasks.add_task(run_demo_job, request.app, job_id)
    return {"job_id": job_id, "status": "demo", "events_url": "/v1/events"}
