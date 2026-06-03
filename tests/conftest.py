# coding: utf-8

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest



@pytest.fixture
def app(monkeypatch, tmpdir) -> FastAPI:
    monkeypatch.setenv("WORKING_DIR", tmpdir)
    from ai_assistant.server.main import app as application
    application.dependency_overrides = {}
    return application


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers() -> dict:
    return {
        "Authorization": "Bearer 098f6bcd4621d373cade4e832627b4f6",
    }
