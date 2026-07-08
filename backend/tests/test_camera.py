from fastapi.testclient import TestClient
from app.main import app
from app.api.camera import get_camera_service
from app.services.camera import MockCamera

client = TestClient(app)


def test_get_status_connected():
    # Подменяем зависимость на мок с подключённой камерой
    mock = MockCamera(connected=True, ip="192.168.1.10", fps=30.0)
    app.dependency_overrides[get_camera_service] = lambda: mock

    response = client.get("/camera/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["ip"] == "192.168.1.10"
    assert data["fps"] == 30.0
    assert data["temperature"] == 42.0

    # Убираем переопределение, чтобы не влиять на другие тесты
    app.dependency_overrides.pop(get_camera_service)


def test_get_status_disconnected():
    mock = MockCamera(connected=False)
    app.dependency_overrides[get_camera_service] = lambda: mock

    response = client.get("/camera/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["ip"] is None
    assert data["fps"] == 0.0

    app.dependency_overrides.pop(get_camera_service)


def test_connect():
    mock = MockCamera(connected=False)
    app.dependency_overrides[get_camera_service] = lambda: mock

    response = client.post("/camera/connect", json={"ip": "192.168.1.50"})
    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Проверяем, что статус обновился
    status = client.get("/camera/status").json()
    assert status["connected"] is True
    assert status["ip"] == "192.168.1.50"

    app.dependency_overrides.pop(get_camera_service)


def test_disconnect():
    mock = MockCamera(connected=True, ip="192.168.1.50")
    app.dependency_overrides[get_camera_service] = lambda: mock

    response = client.post("/camera/disconnect")
    assert response.status_code == 200
    assert response.json() == {"success": True}

    status = client.get("/camera/status").json()
    assert status["connected"] is False

    app.dependency_overrides.pop(get_camera_service)