import pytest
from fastapi.testclient import TestClient

from ironguard_api.main import create_app


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("IRONGUARD_MODEL", "stub")
    return create_app(artifacts=tmp_path, store=tmp_path / "store")


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
