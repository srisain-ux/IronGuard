import pytest
from fastapi.testclient import TestClient

from ironguard_api.main import create_app


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("IRONGUARD_MODEL", "stub")
    # Tests never reach a real Nemotron: the Safeguard agent falls back to its rule card.
    monkeypatch.delenv("NEMOTRON_BASE_URL", raising=False)
    monkeypatch.setattr("ironguard_api.agent.nemotron._client", None)
    return create_app(artifacts=tmp_path, store=tmp_path / "store")


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
