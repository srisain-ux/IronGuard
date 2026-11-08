"""Read-only demo references shared by verification and PII masking."""

import json
from pathlib import Path
from typing import TypedDict, cast


class OfficialContact(TypedDict):
    brand: str
    aliases: list[str]
    domains: list[str]
    phones: list[str]
    contact_url: str


class Directory(TypedDict):
    label: str
    notice: str
    brands: list[OfficialContact]


def load_directory() -> Directory:
    # No mutable global cache: callers cannot alter later verification results.
    path = Path(__file__).resolve().parents[1] / "data" / "official_directory.json"
    return cast(Directory, json.loads(path.read_text(encoding="utf-8")))
