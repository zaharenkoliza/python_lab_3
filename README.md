# Стенд: влияние асинхронных драйверов БД на производительность FastAPI

Практическая работа № 3 (часть 1/2). Полный отчёт: [REPORT.md](REPORT.md).

Сравниваются три драйвера PostgreSQL в одном и том же FastAPI-сервисе:
`psycopg2` (синхронный, в пуле потоков), `asyncpg` и `psycopg 3` (асинхронные).

## Требования
Docker, Docker Compose, `uv`; не менее 6 ядер и 8 ГБ памяти для Docker.

## Запуск
```bash
uv sync --frozen
make build
make pilot      # пилот: 32 прогона, около 16 минут, затем анализ
make full       # полный план: 200 прогонов, около 5 часов
make analyze DIR=results/pilot
make down       # остановить стенд
```
Результаты: `results/<pilot|raw>/` (`runs.csv`, `summary.csv`, сырые CSV и манифесты прогонов).
Параметры эксперимента — в `configs/*.yaml`. На macOS команда compose — `docker-compose`;
для `docker compose` задайте `COMPOSE="docker compose"`.

`make env` печатает параметры машины и Docker (таблица для раздела 6.3 отчёта).

## Быстрый запуск на чистой ВМ (Ubuntu/Debian)
```bash
git clone https://github.com/zaharenkoliza/python_lab_3 && cd python_lab_3
bash scripts/vm_run.sh
```
Скрипт ставит зависимости, собирает стенд, сохраняет параметры машины в `docs/environment.md`, запускает пилот и выводит `docker ps` и итоговые таблицы.
