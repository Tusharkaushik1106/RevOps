import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "apps/api"))
from app.main import app
from fastapi.testclient import TestClient


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["phase"] == "0-foundation"
