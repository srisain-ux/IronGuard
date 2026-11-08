"""FastAPI entry point. All customer text is ephemeral; inference loads once."""

import json
import logging
import os
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .contracts import ROOT, example, validate
from .events import EventBus
from .events import router as events_router
from .model import FixtureModel, load_model
from .routes import agent, chloroplasts, meta, reef, score, zero_day


def create_app(*, artifacts: Path | None = None, store: Path | None = None):
    @asynccontextmanager
    async def lifespan(app):
        configured = Path(os.getenv("IRONGUARD_ARTIFACTS", "../ml/artifacts"))
        app.state.artifacts = artifacts or (
            configured if configured.is_absolute() else ROOT / "api" / configured
        )
        app.state.mode = os.getenv("IRONGUARD_MODEL", "stub")
        weights = ("preynet.pt", "preynet.onnx")
        if app.state.mode == "preynet" and not any(
            (app.state.artifacts / name).is_file() for name in weights
        ):
            # /health then reports "stub", so nobody mistakes the stub for the real model.
            logging.getLogger(__name__).warning("PreyNet artifacts missing; serving the stub")
            app.state.mode = "stub"
        app.state.model = load_model(app.state.mode, app.state.artifacts)
        app.state.fixture = isinstance(app.state.model, FixtureModel)
        app.state.events = EventBus()
        app.state.reef = deque(maxlen=1000)
        app.state.chloroplasts = {}
        directory = store or ROOT / "api" / "store" / "chloroplasts"
        for path in sorted(directory.glob("*.json")):
            manifest = validate("chloroplast", json.loads(path.read_text()), status=500)
            app.state.chloroplasts[manifest["id"]] = manifest
        if app.state.mode == "stub" and not app.state.chloroplasts:
            demo = example("chloroplast.parking.json")
            app.state.chloroplasts[demo["id"]] = validate("chloroplast", demo, status=500)
        yield
        app.state.reef.clear()
        app.state.chloroplasts.clear()
        app.state.model = None

    app = FastAPI(title="IronGuard API", version="0.1.0", lifespan=lifespan)
    origins = [
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if item.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    for router in (
        meta.router,
        score.router,
        agent.router,
        zero_day.router,
        chloroplasts.router,
        reef.router,
        events_router,
    ):
        app.include_router(router)
    return app


app = create_app()
