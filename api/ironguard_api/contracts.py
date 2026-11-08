"""Shared JSON Schema validators; errors never echo customer payloads."""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "contracts" / "schemas" / f"{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate(name: str, value: object, *, status: int = 422):
    if not validator(name).is_valid(value):
        raise HTTPException(status, detail=f"Invalid {name} payload")
    return value


def example(filename: str):
    return json.loads((ROOT / "contracts" / "examples" / filename).read_text())
