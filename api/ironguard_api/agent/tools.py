"""Read-only verification tools. No tool logs input, submits reports, or writes files."""

import re
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Literal, NotRequired, TypedDict

import httpx

from ..directory import OfficialContact, load_directory
from ..scrub import scrub


class ContactResult(TypedDict):
    directory_label: str
    notice: str
    contact: OfficialContact | None


class DomainResult(TypedDict):
    domain: str
    directory_label: str
    official_brands: list[str]
    closest_official_domain: str
    lookalike_distance: int
    possible_lookalike: bool
    rdap_status: Literal["ok", "not_found", "unavailable"]
    age_days: int | None
    registrar: str | None


class NumberResult(TypedDict):
    normalized: str | None
    valid_format: bool
    directory_label: str
    official_brands: list[str]
    fictional: bool
    toll_free: bool
    notice: str


class ReefReport(TypedDict):
    consent: Literal[True]
    channel: Literal["sms", "imessage", "rcs", "whatsapp", "email", "other"]
    family_guess: str
    stage_sequence: list[Literal["benign", "bait", "pivot", "hook", "strike"]]
    template_text: str
    source: NotRequired[Literal["photon", "web"]]


def lookup_official_contact(brand: str) -> ContactResult:
    """Exact, case-insensitive name/alias lookup; unknown brands stay unknown."""
    directory = load_directory()
    key = " ".join(brand.split()).casefold()
    contact = next(
        (
            entry
            for entry in directory["brands"]
            if key in {name.casefold() for name in [entry["brand"], *entry["aliases"]]}
        ),
        None,
    )
    return {
        "directory_label": directory["label"],
        "notice": directory["notice"],
        "contact": contact,
    }


def _domain(value: str) -> str:
    try:
        domain = value.strip().rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise ValueError("Expected a DNS domain name") from None
    labels = domain.split(".")
    if (
        len(domain) > 253
        or len(labels) < 2
        or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
    ):
        raise ValueError("Expected a DNS domain name")
    try:
        ip_address(domain)
    except ValueError:
        return domain
    raise ValueError("Expected a DNS domain name")


def _distance(left: str, right: str) -> int:
    """Levenshtein edit distance, with one row of storage."""
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def _rdap_metadata(data: dict, now: datetime) -> tuple[int | None, str | None]:
    age = None
    for event in data.get("events", []):
        if not isinstance(event, dict) or event.get("eventAction") != "registration":
            continue
        try:
            created = datetime.fromisoformat(event["eventDate"])
            if created.tzinfo is not None and created <= now:
                age = (now - created).days
                break
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    registrar = None
    for entity in data.get("entities", []):
        if not isinstance(entity, dict) or "registrar" not in entity.get("roles", []):
            continue
        card = entity.get("vcardArray", [])
        if not isinstance(card, list) or len(card) != 2 or not isinstance(card[1], list):
            continue
        for field in card[1]:
            if (
                isinstance(field, list)
                and len(field) == 4
                and field[0] == "fn"
                and isinstance(field[3], str)
            ):
                registrar = field[3]
                break
        if registrar:
            break
    return age, registrar


def check_domain(domain: str, *, now: datetime | None = None) -> DomainResult:
    """Query rdap.org and follow its referrals to registry RDAP services.

    Distance is over the full ASCII hostname, not a spoof-detection guarantee.
    Missing RDAP data stays unknown. Official subdomains match on a dot boundary.
    """
    normalized = _domain(domain)
    directory = load_directory()
    domains = [d for entry in directory["brands"] for d in entry["domains"]]
    closest = min(domains, key=lambda d: (_distance(normalized, d), d))
    distance = _distance(normalized, closest)
    brands = [
        entry["brand"]
        for entry in directory["brands"]
        if any(normalized == d or normalized.endswith("." + d) for d in entry["domains"])
    ]
    result: DomainResult = {
        "domain": normalized,
        "directory_label": directory["label"],
        "official_brands": brands,
        "closest_official_domain": closest,
        "lookalike_distance": distance,
        "possible_lookalike": not brands and 0 < distance <= 2,
        "rdap_status": "unavailable",
        "age_days": None,
        "registrar": None,
    }
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        raise ValueError("now must include a timezone")
    try:
        response = httpx.get(
            f"https://rdap.org/domain/{normalized}",
            timeout=5.0,
            follow_redirects=True,
        )
        if response.status_code == 404:
            result["rdap_status"] = "not_found"
            return result
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return result
        result["age_days"], result["registrar"] = _rdap_metadata(data, reference)
        result["rdap_status"] = "ok"
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    return result


def check_number(phone: str) -> NumberResult:
    """Conservative E.164 formatting; bare 10-digit numbers assume US/Canada.

    Format and toll-free flags do not verify assignment, ownership, or caller ID.
    """
    compact = re.sub(r"[ ().-]", "", phone.strip())
    if re.fullmatch(r"[2-9][0-9]{2}[2-9][0-9]{6}", compact):
        compact = "+1" + compact
    elif re.fullmatch(r"1[2-9][0-9]{2}[2-9][0-9]{6}", compact):
        compact = "+" + compact
    valid = bool(re.fullmatch(r"\+[1-9][0-9]{1,14}", compact))
    if compact.startswith("+1"):
        valid = valid and bool(re.fullmatch(r"\+1[2-9][0-9]{2}[2-9][0-9]{6}", compact))
    normalized = compact if valid else None
    nanp = compact[2:] if valid and compact.startswith("+1") else ""
    directory = load_directory()
    return {
        "normalized": normalized,
        "valid_format": valid,
        "directory_label": directory["label"],
        "official_brands": [
            entry["brand"] for entry in directory["brands"] if normalized in entry["phones"]
        ],
        "fictional": bool(nanp and nanp[3:6] == "555" and 100 <= int(nanp[6:]) <= 199),
        "toll_free": bool(nanp and nanp[:3] in {"800", "833", "844", "855", "866", "877", "888"}),
        "notice": "Bare 10-digit numbers assume US/Canada. Format, directory matches and "
        "toll-free prefixes do not authenticate caller ID or prove safety.",
    }


def scrub_and_report(text: str) -> ReefReport:
    """Build an in-memory, schema-shaped draft; never queue or send it.

    Invoke only after explicit reporting consent. Consent is a caller precondition,
    not inferred from text. Unknown channel/family/stages remain unspecified.
    """
    return {
        "consent": True,
        "channel": "other",
        "family_guess": "unknown",
        "stage_sequence": [],
        "template_text": scrub(text)[:1500],
    }
