"""poseorbit serve's HTTP layer, with no model loaded: bounds and the token."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from poseorbit.api import MAX_PIXELS  # noqa: E402
from poseorbit.server import MAX_BODY_BYTES, create_app  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("POSEORBIT_TOKEN", raising=False)
    return TestClient(create_app())


def test_health_states_the_pixel_bound(client):
    assert client.get("/api/health").json()["limits"]["max_pixels"] == MAX_PIXELS


def test_an_ordinary_bad_request_still_gets_400(client):
    answer = client.post("/api/pose", json={})
    assert answer.status_code == 400
    assert "image_base64" in answer.json()["detail"]


def test_a_body_past_the_bound_gets_413(client):
    answer = client.post("/api/pose", content=b" " * (MAX_BODY_BYTES + 1), headers={"content-type": "application/json"})
    assert answer.status_code == 413


def test_a_chunked_body_past_the_bound_gets_413(client):
    def chunks():
        piece = b" " * (1024 * 1024)
        for _ in range(MAX_BODY_BYTES // len(piece) + 2):
            yield piece

    answer = client.post("/api/pose", content=chunks(), headers={"content-type": "application/json"})
    assert answer.status_code == 413


def test_the_token_is_checked(monkeypatch):
    monkeypatch.setenv("POSEORBIT_TOKEN", "secret-token")
    client = TestClient(create_app())
    assert client.post("/api/pose", json={}).status_code == 401
    assert client.post("/api/pose", json={}, headers={"authorization": "Bearer wrong"}).status_code == 401
    assert client.post("/api/pose", json={}, headers={"authorization": "Bearer secret-token"}).status_code == 400
    assert client.get("/api/health").status_code == 200
