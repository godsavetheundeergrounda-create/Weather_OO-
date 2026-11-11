import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from weather_aggregator import CityWeather, GeoCoordinates, WeatherReport
from weather_aggregator.web import create_app

LOC = GeoCoordinates("Токио", 35.68, 139.69, "Япония")


class StubAggregator:
    """Подменяет MultiUserWeatherAggregator: возвращает заготовку или поднимает ошибку."""

    def __init__(self, result=None, error=None):
        self._result, self._error = result, error

    async def fetch_city_weather(self, city):
        if self._error:
            raise self._error
        return self._result


def client_for(aggregator):
    isolated_db = Path(tempfile.mkdtemp()) / "test.sqlite3"
    return TestClient(create_app(aggregator=aggregator, database_path=isolated_db))


def test_weather_ok():
    data = CityWeather(
        LOC,
        reports=[
            WeatherReport("Open-Meteo API", 10.0, 5.0, "Ясно", condition_code=0),
            WeatherReport("Wttr.in Service", 12.0, 7.0, "Sunny"),
        ],
        errors=[],
    )
    with client_for(StubAggregator(data)) as client:
        resp = client.get("/api/weather", params={"city": "  Токио "})
    assert resp.status_code == 200
    body = resp.json()
    assert body["city"] == "Токио"
    assert body["average_temp"] == 11.0
    assert body["icon"] == "☀️"
    assert [r["provider"] for r in body["reports"]] == ["Open-Meteo API", "Wttr.in Service"]


def test_city_not_found_is_404():
    with client_for(StubAggregator(error=ValueError("нет такого"))) as client:
        resp = client.get("/api/weather", params={"city": "Нигдеград"})
    assert resp.status_code == 404
    assert "Нигдеград" in resp.json()["detail"]


def test_geocoder_down_is_502():
    with client_for(StubAggregator(error=RuntimeError("упал"))) as client:
        resp = client.get("/api/weather", params={"city": "Токио"})
    assert resp.status_code == 502


def test_all_sources_failed_is_502():
    data = CityWeather(LOC, reports=[], errors=["a", "b"])
    with client_for(StubAggregator(data)) as client:
        resp = client.get("/api/weather", params={"city": "Токио"})
    assert resp.status_code == 502


@pytest.mark.parametrize("city", ["", "   "])
def test_blank_city_is_400(city):
    with client_for(StubAggregator()) as client:
        resp = client.get("/api/weather", params={"city": city})
    assert resp.status_code == 400


def test_frontend_is_served():
    with client_for(StubAggregator()) as client:
        index = client.get("/")
        js = client.get("/app.js")
        health = client.get("/api/health")
    assert index.status_code == 200 and "<title>" in index.text
    assert js.status_code == 200
    assert health.json() == {"status": "ok"}


def test_registration_login_and_personal_favorites(tmp_path):
    database = tmp_path / "users.sqlite3"
    first = TestClient(create_app(StubAggregator(), database_path=database))
    second = TestClient(create_app(StubAggregator(), database_path=database))

    # Первый пользователь регистрируется и получает серверную сессию.
    registered = first.post(
        "/api/auth/register",
        json={"username": "ivan", "email": "ivan@example.com", "password": "strong-pass-123"},
    )
    assert registered.status_code == 200
    first_user = registered.json()
    assert first_user["authenticated"] is True
    assert first_user["user"]["username"] == "ivan"
    assert "password" not in registered.text
    assert first.cookies.get("weather_session")
    assert "httponly" in registered.headers.get("set-cookie", "").lower()

    csrf_first = first_user["csrf_token"]
    assert first.get("/api/favorites").json() == {"favorites": []}

    # Избранный город сохраняется для первого аккаунта; повтор не создаёт дубль.
    added = first.post(
        "/api/favorites", json={"city": "  Санкт-Петербург "}, headers={"X-CSRF-Token": csrf_first}
    )
    assert added.status_code == 200
    favorite_id = added.json()["favorite"]["id"]
    first.post(
        "/api/favorites", json={"city": "санкт-петербург"}, headers={"X-CSRF-Token": csrf_first}
    )
    assert len(first.get("/api/favorites").json()["favorites"]) == 1

    # Избранное остаётся в базе после выхода и повторного входа.
    first.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_first})
    first_login = first.post(
        "/api/auth/login", json={"email": "ivan@example.com", "password": "strong-pass-123"}
    )
    assert first_login.status_code == 200
    assert len(first.get("/api/favorites").json()["favorites"]) == 1

    # Другой пользователь получает пустой список и не может удалить чужой город.
    second_registered = second.post(
        "/api/auth/register",
        json={"username": "maria", "email": "maria@example.com", "password": "another-pass-456"},
    )
    assert second_registered.status_code == 200
    csrf_second = second_registered.json()["csrf_token"]
    assert second.get("/api/favorites").json() == {"favorites": []}
    forbidden_delete = second.delete(
        f"/api/favorites/{favorite_id}", headers={"X-CSRF-Token": csrf_second}
    )
    assert forbidden_delete.status_code == 404
    assert len(first.get("/api/favorites").json()["favorites"]) == 1

    # Повторный вход восстанавливает доступ к тем же персональным данным.
    second.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_second})
    login = second.post(
        "/api/auth/login", json={"email": "MARIA@example.com", "password": "another-pass-456"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["username"] == "maria"
    assert second.get("/api/auth/me").json()["authenticated"] is True
    assert second.get("/api/favorites").json() == {"favorites": []}

    # Logout закрывает сессию.
    csrf_after_login = login.json()["csrf_token"]
    logged_out = second.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_after_login})
    assert logged_out.status_code == 204
    assert second.get("/api/favorites").status_code == 401


def test_auth_validation_and_csrf(tmp_path):
    with TestClient(create_app(StubAggregator(), database_path=tmp_path / "auth.sqlite3")) as client:
        assert client.get("/api/favorites").status_code == 401
        invalid = client.post(
            "/api/auth/register",
            json={"username": "ab", "email": "not-an-email", "password": "123"},
        )
        assert invalid.status_code == 422

        registered = client.post(
            "/api/auth/register",
            json={"username": "tester", "email": "test@example.com", "password": "password-123"},
        )
        assert registered.status_code == 200
        assert client.post(
            "/api/favorites", json={"city": "Москва"}
        ).status_code == 403

        duplicate = client.post(
            "/api/auth/register",
            json={"username": "tester2", "email": "TEST@example.com", "password": "password-456"},
        )
        assert duplicate.status_code == 409
        duplicate_name = client.post(
            "/api/auth/register",
            json={"username": "TESTER", "email": "other@example.com", "password": "password-456"},
        )
        assert duplicate_name.status_code == 409

        wrong_password = client.post(
            "/api/auth/login", json={"email": "test@example.com", "password": "wrong-password"}
        )
        assert wrong_password.status_code == 401
