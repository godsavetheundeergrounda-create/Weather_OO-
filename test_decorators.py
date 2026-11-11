import asyncio

import aiohttp
import pytest

from weather_aggregator.decorators import async_retry, async_ttl_cache


def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    @async_retry(retries=3, delay=0)
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise asyncio.TimeoutError()
        return "ok"

    assert asyncio.run(flaky()) == "ok"
    assert calls["n"] == 3


def test_retry_raises_runtime_error_with_cause():
    @async_retry(retries=2, delay=0)
    async def always_fails():
        raise aiohttp.ClientError("boom")

    with pytest.raises(RuntimeError) as exc:
        asyncio.run(always_fails())
    assert isinstance(exc.value.__cause__, aiohttp.ClientError)


def test_retry_does_not_swallow_other_errors():
    @async_retry(retries=3, delay=0)
    async def bad():
        raise ValueError("не сетевая ошибка")

    with pytest.raises(ValueError):
        asyncio.run(bad())


def test_ttl_cache_runs_once_for_concurrent_calls():
    class Service:
        calls = 0

        @async_ttl_cache(ttl_seconds=60)
        async def get(self, key):
            Service.calls += 1
            await asyncio.sleep(0.01)
            return key.upper()

    async def scenario():
        s = Service()
        return await asyncio.gather(*(s.get("moscow") for _ in range(10)))

    assert asyncio.run(scenario()) == ["MOSCOW"] * 10
    assert Service.calls == 1


def test_ttl_cache_expires():
    class Service:
        calls = 0

        @async_ttl_cache(ttl_seconds=0)
        async def get(self, key):
            Service.calls += 1
            return key

    async def scenario():
        s = Service()
        await s.get("a")
        await s.get("a")

    asyncio.run(scenario())
    assert Service.calls == 2


def test_ttl_cache_cache_if_skips_bad_results():
    class Service:
        calls = 0

        @async_ttl_cache(ttl_seconds=60, cache_if=lambda r: r is not None)
        async def get(self, key):
            Service.calls += 1

    async def scenario():
        s = Service()
        await s.get("a")
        await s.get("a")

    asyncio.run(scenario())
    assert Service.calls == 2
