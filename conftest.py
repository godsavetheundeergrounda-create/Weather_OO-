"""Общие тестовые заглушки: подменяют aiohttp-сессию, сеть не нужна."""

from __future__ import annotations

import aiohttp


class FakeResponse:
    def __init__(self, payload, status: int = 200):
        self._payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(None, (), status=self.status)

    async def json(self):
        return self._payload


class FakeSession:
    """Возвращает заготовленные ответы по очереди; Exception в очереди — поднимается."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        item = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        if isinstance(item, BaseException):
            raise item
        return item if isinstance(item, FakeResponse) else FakeResponse(item)
