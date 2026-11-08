"""Load upstream ML once; fixtures are an explicit scaffold, never a real forecast."""

import importlib
import logging

from .contracts import example


class FixtureModel:
    def score(self, turns, chloroplasts):
        result = example("score_response.turn3.json")
        result["model"] = {"name": "stub", "version": "contract-fixture", "runtime": "python"}
        result["attention"] = [1 / len(turns)] * len(turns)
        result["evidence"] = []
        return result


def load_model(mode: str, artifacts):
    if mode not in {"stub", "preynet"}:
        raise RuntimeError("IRONGUARD_MODEL must be stub or preynet")
    module = "ironguard_ml.stub" if mode == "stub" else "ironguard_ml.infer"
    try:
        implementation = importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if mode != "stub" or exc.name not in {"ironguard_ml", module}:
            raise
        logging.getLogger(__name__).warning("ML stub unavailable; using labeled contract fixture")
        return FixtureModel()
    return implementation.load(str(artifacts))
