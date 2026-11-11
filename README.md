# 🌦 weather-aggregator

Асинхронный многопользовательский агрегатор погоды с веб-интерфейсом, регистрацией и персональным списком избранных городов. У каждого аккаунта собственные избранные города и серверная сессия. Для запрошенного города приложение конкурентно опрашивает несколько открытых погодных API, усредняет температуру и аккуратно переживает падение отдельных источников.

**Веб-интерфейс:** FastAPI-бэкенд + лёгкий фронтенд без сборки (HTML/CSS/JS), тёмная тема, фон меняет цвет в зависимости от температуры, адаптивная вёрстка.

## Быстрый запуск одним файлом

После распаковки репозитория программу можно запустить без ручной настройки окружения:

- **Windows:** дважды щёлкните `start.bat` в корневой папке проекта.
- **Linux / macOS:** откройте терминал в папке проекта и выполните `./start.sh`.

При первом запуске сценарий сам создаст виртуальное окружение `.venv` и установит проект вместе с зависимостями. При следующих запусках он использует уже готовое окружение и сразу запускает веб-сервер. Если вы изменили зависимости в `pyproject.toml`, удалите папку `.venv` — она будет создана заново при следующем запуске. Нужен Python 3.10 или новее и подключение к интернету для установки пакетов и получения погоды. Окно командной строки остаётся открытым после остановки приложения; при ошибке установки подробный вывод сохраняется в `weather-aggregator-startup.log` в корне проекта.

По умолчанию откроется браузер с адресом http://localhost:8000. Введите город и нажмите «Найти». Чтобы сохранять избранные города отдельно для своего аккаунта, нажмите «Регистрация», создайте аккаунт, а затем используйте кнопку «В избранное» в карточке погоды. После повторного входа список избранного восстановится. Ссылкой на конкретный город можно поделиться: `http://localhost:8000/?city=Токио`.

Дополнительные параметры можно передавать сценарию запуска, например `start.bat --port 3000` или `./start.sh --port 3000 --no-browser`. Для доступа из локальной сети используйте `--host 0.0.0.0`. Автодокументация API: http://localhost:8000/docs.

### Ручной запуск (альтернатива)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
python -m weather_aggregator.web     # или: weather-web
```

Проект демонстрирует на практике:

- **ООП и полиморфизм** — единый интерфейс `BaseWeatherProvider`, новые источники добавляются наследованием;
- **Декораторы** — `@async_timer`, `@async_retry`, `@async_ttl_cache` для асинхронных функций;
- **asyncio / aiohttp** — единый пул соединений, `asyncio.gather` для параллельных запросов;
- **Защиту от cache stampede** — при одновременных запросах об одном городе в сеть уходит один запрос.

## Источники данных

| Назначение | Сервис |
|---|---|
| Геокодинг (город → координаты) | [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) |
| Погода | [Open-Meteo](https://open-meteo.com), [wttr.in](https://wttr.in) |

API-ключи не нужны.

## Структура проекта

```
weather-aggregator/
├── src/weather_aggregator/
│   ├── decorators.py        # async_timer, async_retry, async_ttl_cache
│   ├── models.py            # GeoCoordinates, WeatherReport, CityWeather, UserSession
│   ├── geocoding.py         # GeocodingService
│   ├── providers/
│   │   ├── base.py          # BaseWeatherProvider (ABC)
│   │   ├── open_meteo.py    # OpenMeteoProvider
│   │   └── wttr_in.py       # WttrInProvider
│   ├── aggregator.py        # MultiUserWeatherAggregator
│   ├── formatting.py        # текстовый отчёт
│   ├── weather_codes.py     # расшифровка кодов WMO (текст + эмодзи)
│   ├── web/
│   │   ├── app.py           # FastAPI: погода, регистрация, вход и избранное
│   │   ├── auth.py          # SQLite-хранилище пользователей, сессий и избранного
│   │   ├── __main__.py      # запуск сервера (uvicorn)
│   │   └── static/          # фронтенд: index.html, style.css, app.js
│   ├── cli.py               # консольный интерфейс (город / интерактив / --demo)
│   ├── demo.py              # симуляция 4 одновременных пользователей
│   └── __main__.py          # python -m weather_aggregator
├── tests/                   # pytest, без обращения к сети
├── notebooks/
│   └── weather_prototype.ipynb   # исходный прототип в Jupyter
├── .github/workflows/ci.yml # ruff + pytest на Python 3.10–3.12
├── pyproject.toml
└── requirements.txt
```

## Аккаунты и избранные города

- Регистрация: `POST /api/auth/register` с JSON `{"username":"alex","email":"alex@example.com","password":"пароль-от-8-символов"}`.
- Вход: `POST /api/auth/login` с JSON `{"email":"alex@example.com","password":"..."}`.
- Текущий пользователь: `GET /api/auth/me`.
- Выход: `POST /api/auth/logout`.
- Список избранного: `GET /api/favorites`.
- Добавление города: `POST /api/favorites` с JSON `{"city":"Токио"}`.
- Удаление города: `DELETE /api/favorites/{id}`.

После входа сервер выдаёт HttpOnly-cookie сессии и CSRF-токен. Запросы, изменяющие данные, должны передавать токен в заголовке `X-CSRF-Token`; веб-интерфейс делает это автоматически. Пароли хранятся только в виде salted PBKDF2-HMAC-SHA256-хешей. Сессии и избранные города хранятся в SQLite, а операции со списком всегда ограничены ID текущего пользователя.

По умолчанию база создаётся в `data/weather_aggregator.sqlite3` относительно папки запуска. Путь можно переопределить переменной окружения `WEATHER_DATABASE_PATH`. Для HTTPS-развёртывания установите `WEATHER_COOKIE_SECURE=1`, чтобы cookie передавалась только по защищённому соединению. Локальный запуск по HTTP оставляет этот параметр выключенным.

Это базовая версия учётных записей: подтверждение email, восстановление забытого пароля и ограничение частоты попыток входа пока не реализованы. Для публичного интернет-развёртывания дополнительно нужны HTTPS, надёжная конфигурация reverse proxy, rate limiting и резервное копирование базы.

## API погоды

`GET /api/weather?city=Токио`

```json
{
  "city": "Токио", "country": "Япония", "latitude": 35.69, "longitude": 139.69,
  "average_temp": 11.5, "icon": "☀️",
  "reports": [
    {"provider": "Open-Meteo API", "temperature_c": 11.0, "wind_speed_kmh": 7.2, "description": "Ясно"}
  ],
  "errors": []
}
```

Коды ответа: `404` — город не найден, `502` — внешние сервисы недоступны, `400` — пустой запрос. Если часть источников упала, ответ всё равно `200`, а ошибки перечислены в `errors`.

## Консоль

Без браузера погоду можно узнать и из терминала (`pip install -e .` уже сделан):

```bash
python -m weather_aggregator Екатеринбург        # один или несколько городов
python -m weather_aggregator Токио Белград
python -m weather_aggregator                     # интерактивный режим: вводишь города по одному
python -m weather_aggregator Токио -v            # + таймеры запросов и кэш
```

После `pip install -e .` то же самое доступно командой `weather Екатеринбург`.

Демо с четырьмя «пользователями» одновременно (двое спрашивают Екатеринбург — второй запрос идёт из кэша):

```bash
python -m weather_aggregator --demo              # или: weather-demo
```

## Использование как библиотеки

```python
import asyncio
import aiohttp

from weather_aggregator import (
    GeocodingService, MultiUserWeatherAggregator,
    OpenMeteoProvider, WttrInProvider,
)

async def main():
    async with aiohttp.ClientSession() as session:
        app = MultiUserWeatherAggregator(
            GeocodingService(session),
            [OpenMeteoProvider(session), WttrInProvider(session)],
        )
        data = await app.fetch_city_weather("Екатеринбург")
        print(data.location.city, data.average_temp, data.errors)

asyncio.run(main())
```

## Как добавить новый источник погоды

```python
from weather_aggregator import BaseWeatherProvider, WeatherReport

class MyProvider(BaseWeatherProvider):
    @property
    def name(self) -> str:
        return "My API"

    async def get_weather(self, coords) -> WeatherReport:
        ...  # запрос через self._session
```

Передайте экземпляр в список провайдеров агрегатора — больше ничего менять не нужно. При желании оберните метод в `@async_retry` и `@async_timer`.

## Разработка

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

Тесты используют заглушки вместо `aiohttp.ClientSession`, поэтому работают офлайн.

## Идеи для развития

- Telegram-бот поверх того же агрегатора;
- прогноз на несколько дней и почасовой график;
- ещё провайдеры (OpenWeatherMap, WeatherAPI) с ключами из переменных окружения;
- Dockerfile для деплоя;
- Redis вместо in-memory кэша.

## Лицензия

MIT — см. [LICENSE](LICENSE).


### Значок на рабочем столе (Windows)

Чтобы создать ярлык Weather Aggregator с иконкой-солнышком, после распаковки проекта дважды щёлкните `create_desktop_shortcut.bat`. Скрипт создаст ярлык `Weather Aggregator` на рабочем столе и привяжет его к `start.bat` и файлу `weather-sun.ico`. Запускать приложение после этого можно через новый ярлык. Не перемещайте отдельно файл `weather-sun.ico` и саму папку проекта: ярлык использует их расположение. Если папку проекта перенесли, запустите `create_desktop_shortcut.bat` ещё раз.
