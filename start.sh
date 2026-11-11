#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if command -v python3 >/dev/null 2>&1; then
    BASE_PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    BASE_PYTHON="$(command -v python)"
else
    echo "Ошибка: Python 3.10 или новее не найден." >&2
    echo "Установите Python: https://www.python.org/downloads/" >&2
    exit 1
fi

if ! "$BASE_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Ошибка: для проекта требуется Python 3.10 или новее." >&2
    exit 1
fi

VENV_PYTHON=".venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[1/2] Создание виртуального окружения..."
    "$BASE_PYTHON" -m venv .venv || {
        echo "Не удалось создать .venv. Возможно, нужно установить пакет python3-venv." >&2
        exit 1
    }
fi

if [[ ! -f ".venv/.weather-aggregator-installed" ]]; then
    echo "[2/2] Установка зависимостей (первый запуск)..."
    "$VENV_PYTHON" -m pip install --disable-pip-version-check -e .
    touch ".venv/.weather-aggregator-installed"
else
    echo "[2/2] Окружение уже настроено."
fi

echo
echo "Запуск Weather Aggregator..."
echo "Браузер откроется автоматически. Для остановки нажмите Ctrl+C."
echo
exec "$VENV_PYTHON" -m weather_aggregator.web "$@"
