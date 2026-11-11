import asyncio

import pytest
from conftest import FakeSession

from weather_aggregator import (
    BaseWeatherProvider,
    GeocodingService,
    GeoCoordinates,
    MultiUserWeatherAggregator,
    WeatherReport,
)


class StubProvider(BaseWeatherProvider):
    def __init__(self, name, temp=None, fail=False):
        super().__init__(session=None)
        self._name, self._temp, self._fail = name, temp, fail
        self.calls = 0

    @property
    def name(self):
        return self._name

    async def get_weather(self, coords):
        self.calls += 1
        if self._fail:
            raise RuntimeError(f"{self._name} недоступен")
        return WeatherReport(self._name, self._temp, 5.0, "ясно")


GEO_PAYLOAD = {
    "results": [{"name": "Токио", "latitude": 35.68, "longitude": 139.69, "country": "Япония"}]
}


def make_app(*providers):
    geocoder = GeocodingService(FakeSession(GEO_PAYLOAD))
    return MultiUserWeatherAggregator(geocoder, list(providers))


def test_average_and_partial_errors():
    app = make_app(StubProvider("A", 10.0), StubProvider("B", 20.0), StubProvider("C", fail=True))
    data = asyncio.run(app.fetch_city_weather("Токио"))
    assert data.average_temp == 15.0
    assert len(data.reports) == 2
    assert data.errors == ["C недоступен"]


def test_concurrent_requests_hit_providers_once():
    provider = StubProvider("A", 10.0)
    app = make_app(provider)

    async def scenario():
        await asyncio.gather(*(app.fetch_city_weather("Токио") for _ in range(5)))

    asyncio.run(scenario())
    assert provider.calls == 1


def test_all_failed_is_not_cached():
    provider = StubProvider("A", fail=True)
    app = make_app(provider)

    async def scenario():
        first = await app.fetch_city_weather("Токио")
        await app.fetch_city_weather("Токио")
        return first

    first = asyncio.run(scenario())
    assert first.average_temp is None
    assert provider.calls == 2


def test_city_not_found():
    geocoder = GeocodingService(FakeSession({"results": []}))
    app = MultiUserWeatherAggregator(geocoder, [StubProvider("A", 1.0)])
    with pytest.raises(ValueError):
        asyncio.run(app.fetch_city_weather("Нигдеград"))


def test_geocoding_parses_coordinates():
    geocoder = GeocodingService(FakeSession(GEO_PAYLOAD))
    coords = asyncio.run(geocoder.get_coordinates("Токио"))
    assert coords == GeoCoordinates("Токио", 35.68, 139.69, "Япония")
