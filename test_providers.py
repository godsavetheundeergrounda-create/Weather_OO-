import asyncio

import pytest
from conftest import FakeSession

from weather_aggregator.models import GeoCoordinates
from weather_aggregator.providers import OpenMeteoProvider, WttrInProvider

COORDS = GeoCoordinates("Екатеринбург", 56.85, 60.61, "Россия")


def test_open_meteo_parses_response():
    session = FakeSession(
        {"current_weather": {"temperature": -5.5, "windspeed": 12.0, "weathercode": 3}}
    )
    report = asyncio.run(OpenMeteoProvider(session).get_weather(COORDS))
    assert report.provider_name == "Open-Meteo API"
    assert report.temperature_c == -5.5
    assert report.wind_speed_kmh == 12.0
    assert report.description == "Пасмурно"
    assert report.condition_code == 3


def test_wttr_in_parses_response():
    session = FakeSession(
        {
            "current_condition": [
                {"temp_C": "-4", "windspeedKmph": "10", "weatherDesc": [{"value": "Cloudy"}]}
            ]
        }
    )
    report = asyncio.run(WttrInProvider(session).get_weather(COORDS))
    assert report.provider_name == "Wttr.in Service"
    assert report.temperature_c == -4.0
    assert report.description == "Cloudy"


def test_provider_retries_then_fails():
    session = FakeSession(asyncio.TimeoutError())
    with pytest.raises(RuntimeError):
        asyncio.run(OpenMeteoProvider(session).get_weather(COORDS))
    assert len(session.calls) == 2  # retries=2
