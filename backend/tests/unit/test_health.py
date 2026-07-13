"""Health endpoint unit tests."""

from fastapi.testclient import TestClient

from app.main import create_app


class HealthyDatabase:
    """Database double that reports a successful readiness probe."""

    async def check(self) -> None:
        """Simulate a responsive database."""

    async def close(self) -> None:
        """Match the application database lifecycle contract."""


class UnavailableDatabase:
    """Database double that fails its readiness probe."""

    async def check(self) -> None:
        """Simulate an unavailable database."""

        raise RuntimeError("database unavailable")

    async def close(self) -> None:
        """Match the application database lifecycle contract."""


def test_health_reports_ready_database() -> None:
    """AC-1: health returns the documented ready payload."""

    app = create_app()
    with TestClient(app) as client:
        app.state.database = HealthyDatabase()
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0", "db": "ok"}


def test_health_reports_unavailable_database() -> None:
    """Health degrades cleanly when the database readiness probe fails."""

    app = create_app()
    with TestClient(app) as client:
        app.state.database = UnavailableDatabase()
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["db"] == "unavailable"
