#!/usr/bin/env bash
# Подготовка чистой ВМ (Ubuntu/Debian) и запуск пилота одной командой:
#   bash scripts/vm_run.sh            # установка зависимостей, сборка, пилот
#   SKIP_INSTALL=1 bash scripts/vm_run.sh   # если Docker и uv уже установлены
# Запускать из корня репозитория, в домашней папке. Во время прогона ничего другого не запускать.
set -euo pipefail

if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  sudo apt-get update -y
  sudo apt-get install -y docker.io docker-compose-v2 git make python3-pip pipx
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" || true
  pipx install uv || true
  export PATH="$HOME/.local/bin:$PATH"
fi

# команда compose: плагин (docker compose) или отдельная (docker-compose)
if docker compose version >/dev/null 2>&1; then export COMPOSE="docker compose"; else export COMPOSE="docker-compose"; fi
DOCKER="docker"; docker ps >/dev/null 2>&1 || DOCKER="sudo docker"   # если группа docker ещё не применилась
echo "compose: $COMPOSE"

mkdir -p docs
uv sync --frozen
make env | tee docs/environment.md        # СКРИНШОТ: параметры ВМ и вставка в раздел 6.3
make build

make pilot > docs/pilot_console.log 2>&1 &
PID=$!
sleep 90
echo "=== docker ps (СКРИНШОТ) ==="; $COMPOSE ps
wait $PID
echo "=== итог пилота (СКРИНШОТ) ==="; tail -30 docs/pilot_console.log
echo "График: docs/pilot_order.png (СКРИНШОТ)"
