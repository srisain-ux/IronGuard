import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from ironguard_api.agent.tools import (
    check_domain,
    check_number,
    lookup_official_contact,
    scrub_and_report,
)
from ironguard_api.contracts import example, validate
from ironguard_api.directory import load_directory
from ironguard_api.scrub import scrub


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        pytest.fail("Unexpected network request")

    monkeypatch.setattr(httpx.Client, "send", reject)
    monkeypatch.setattr(httpx.AsyncClient, "send", reject)


@pytest.fixture
def rdap(monkeypatch):
    data = json.loads((Path(__file__).parent / "fixtures/rdap_domain.json").read_text())
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json=data, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    return data, calls


@pytest.fixture
def now():
    return datetime(2020, 1, 11, tzinfo=UTC)


@pytest.fixture
def raw_report():
    return (
        "Alice from Bank of America: call +1 (214) 555-0123 or alice@example.com; "
        "pay $45.50 at https://pay.example/login. Ask @support.team or T-Mobile."
    )


def test_lookup_directory_and_aliases(rdap):
    result = lookup_official_contact("  citibank  ")
    assert result["directory_label"] == "curated demo directory"
    assert result["contact"]["domains"] == ["citi.com"]
    assert lookup_official_contact("PNC fraud support")["contact"] is None
    result["contact"]["domains"].clear()
    assert lookup_official_contact("Citi")["contact"]["domains"] == ["citi.com"]
    assert not rdap[1]


def test_directory_entries():
    directory = load_directory()
    assert len(directory["brands"]) == 25
    assert directory["label"] == "curated demo directory"
    for contact in directory["brands"]:
        for name in [contact["brand"], *contact["aliases"]]:
            assert lookup_official_contact(name)["contact"] == contact
            assert scrub(name) == "[BRAND]"
        for phone in contact["phones"]:
            assert contact["brand"] in check_number(phone)["official_brands"]
            assert not check_number(phone)["fictional"]


@pytest.mark.parametrize(
    "domain,brands,closest,distance,lookalike",
    [
        (" PNC.COM. ", ["PNC"], "pnc.com", 0, False),
        ("login.pnc.com", ["PNC"], "pnc.com", 6, False),
        ("pncc.com", [], "pnc.com", 1, True),
        ("evilpnc.com", [], "pnc.com", 4, False),
        ("pnc.com.evil.test", [], None, None, False),
        ("bücher.de", [], None, None, False),
    ],
)
def test_domain_rdap_and_lookalike(rdap, now, domain, brands, closest, distance, lookalike):
    result = check_domain(domain, now=now)
    assert result["rdap_status"] == "ok"
    assert result["age_days"] == 10
    assert result["registrar"] == "Fixture Registrar"
    assert result["official_brands"] == brands
    assert result["possible_lookalike"] is lookalike
    if closest:
        assert (result["closest_official_domain"], result["lookalike_distance"]) == (
            closest,
            distance,
        )
    assert rdap[1] == [
        (f"https://rdap.org/domain/{result['domain']}", {"timeout": 5.0, "follow_redirects": True})
    ]
    if domain == "bücher.de":
        assert result["domain"] == "xn--bcher-kva.de"


@pytest.mark.parametrize(
    "domain",
    [
        "",
        "localhost",
        "https://pnc.com",
        "pnc.com/path",
        "pnc.com?x=1",
        "a@pnc.com",
        "127.0.0.1",
        "[::1]",
        "-bad.com",
        "bad_.com",
        "a..com",
        "a" * 64 + ".com",
    ],
)
def test_invalid_domains_never_request(rdap, domain):
    with pytest.raises(ValueError, match="Expected a DNS domain name"):
        check_domain(domain)
    assert not rdap[1]


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (404, {}, "not_found"),
        (429, {}, "unavailable"),
        (503, {}, "unavailable"),
        (200, [], "unavailable"),
        (200, {"events": None}, "unavailable"),
    ],
)
def test_rdap_failures_are_unknown(monkeypatch, now, status, body, expected):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **kwargs: httpx.Response(status, json=body, request=httpx.Request("GET", url)),
    )
    result = check_domain("pncc.com", now=now)
    assert result["rdap_status"] == expected
    assert result["age_days"] is result["registrar"] is None
    assert result["possible_lookalike"]  # Local checks still work on outage/404.


@pytest.mark.parametrize("failure", ["timeout", "bad_json"])
def test_rdap_transport_and_json_errors(monkeypatch, now, failure):
    def get(url, **kwargs):
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture")
        return httpx.Response(200, text="not JSON", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    result = check_domain("pnc.com", now=now)
    assert result["rdap_status"] == "unavailable"
    assert result["age_days"] is result["registrar"] is None


@pytest.mark.parametrize("date", [None, "invalid", "2026-01-01T00:00:00Z", "2020-01-01"])
def test_unusable_registration_date(rdap, now, date):
    rdap[0]["events"][1]["eventDate"] = date
    result = check_domain("pnc.com", now=now)
    assert result["age_days"] is None
    assert result["registrar"] == "Fixture Registrar"


def test_rdap_missing_optional_metadata(rdap, now):
    rdap[0].clear()
    result = check_domain("pnc.com", now=now)
    assert result["age_days"] is result["registrar"] is None


@pytest.mark.parametrize(
    "phone,normalized,brands,fictional,toll_free",
    [
        ("(800) 935-9935", "+18009359935", ["Chase"], False, True),
        ("1-888-762-2265", "+18887622265", ["PNC"], False, True),
        ("+1 (214) 555-0100", "+12145550100", [], True, False),
        ("214-555-0199", "+12145550199", [], True, False),
        ("214-555-0200", "+12145550200", [], False, False),
        ("214-555-0099", "+12145550099", [], False, False),
        ("+44 20 7946 0123", "+442079460123", [], False, False),
        ("+683 1234", "+6831234", [], False, False),
        ("+1-833-234-5678", "+18332345678", [], False, True),
        ("+1-822-234-5678", "+18222345678", [], False, False),
        ("+44 555 012 3456", "+445550123456", [], False, False),
        ("911", None, [], False, False),
        ("1800FLOWERS", None, [], False, False),
        ("+0123456789", None, [], False, False),
        ("+12145550123 ext 5", None, [], False, False),
        ("+1234567890123456", None, [], False, False),
        ("+10005550123", None, [], False, False),
    ],
)
def test_number_heuristics(rdap, phone, normalized, brands, fictional, toll_free):
    result = check_number(phone)
    assert result["normalized"] == normalized
    assert result["valid_format"] is (normalized is not None)
    assert result["official_brands"] == brands
    assert result["fictional"] is fictional
    assert result["toll_free"] is toll_free
    assert not rdap[1]


def test_scrub_and_report_contract(raw_report, rdap):
    report = scrub_and_report(raw_report)
    assert validate("reef_report", report) == report
    assert report["template_text"] == (
        "[NAME] from [BRAND]: call [PHONE] or [EMAIL]; pay [AMOUNT] at [URL] Ask [NAME] or [BRAND]."
    )
    assert report["channel"] == "other"
    assert report["family_guess"] == "unknown"
    assert report["stage_sequence"] == []
    assert scrub_and_report(report["template_text"]) == report
    assert (
        scrub(example("reef_report.photon.json")["template_text"])
        == (example("reef_report.photon.json")["template_text"])
    )
    assert not rdap[1]


def test_report_scrubs_before_truncating(rdap):
    report = scrub_and_report("x " * 747 + "alice@example.com")
    assert len(report["template_text"]) <= 1500
    assert "alice" not in report["template_text"]
    validate("reef_report", report)
    assert scrub_and_report("")["template_text"] == ""


@pytest.mark.parametrize(
    "text,expected",
    [
        ("bücher.de/login", "[URL]"),
        ("www.example.com", "[URL]"),
        ("@support.team", "[NAME]"),
        ("a@example.com", "[EMAIL]"),
        ("support@例子.中国", "[EMAIL]"),
        ("Send 250 USD to @support-team", "Send [AMOUNT] to [NAME]"),
        (
            "[PHONE] [EMAIL] [URL] [AMOUNT] [NAME] [BRAND]",
            "[PHONE] [EMAIL] [URL] [AMOUNT] [NAME] [BRAND]",
        ),
    ],
)
def test_scrub_patterns(text, expected):
    assert scrub(text) == expected
    assert scrub(expected) == expected
