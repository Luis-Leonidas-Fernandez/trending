#!/bin/bash
set -Eeuo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
RELOAD="${RELOAD:-1}"
API_ONLY=0
RUN_PIPELINE=0
INSTALL_DEPS=0
CHECK_ONLY=0

usage() {
  cat <<EOF
Uso:
  ./run.sh [opciones]

Opciones:
  --host HOST          Host para FastAPI. Default: 127.0.0.1
  --port PORT          Puerto para FastAPI. Default: 8000
  --no-reload          Levanta uvicorn sin reload
  --api-only           Levanta sólo FastAPI, sin servidor web estático
  --with-pipeline      Ejecuta Fase 2 -> Fase 3 -> Fase 4 antes de levantar la API
  --install            Crea .venv si falta e instala python_backend/requirements.txt
  --check              Verifica entorno, base y dependencias sin levantar servidor
  -h, --help           Muestra esta ayuda

Variables de entorno útiles:
  PYTHON_BIN           Python a usar. Default: .venv/bin/python
  PYTHON_DB_FILE       Ruta alternativa para SQLite
  HOST                 Host default
  PORT                 Puerto default de FastAPI
  FRONTEND_PORT        Puerto default de la UI estática
  RELOAD               1 para reload, 0 para sin reload

Ejemplos:
  ./run.sh
  ./run.sh --with-pipeline
  ./run.sh --install --with-pipeline
  HOST=0.0.0.0 PORT=8010 FRONTEND_PORT=5174 ./run.sh --no-reload
EOF
}

log() {
  printf '\033[1;34m[trending]\033[0m %s\n' "$1"
}

fail() {
  printf '\033[1;31m[trending:error]\033[0m %s\n' "$1" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      [[ -n "$HOST" ]] || fail "--host necesita un valor"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      [[ -n "$PORT" ]] || fail "--port necesita un valor"
      shift 2
      ;;
    --no-reload)
      RELOAD=0
      shift
      ;;
    --api-only)
      API_ONLY=1
      shift
      ;;
    --with-pipeline)
      RUN_PIPELINE=1
      shift
      ;;
    --install)
      INSTALL_DEPS=1
      shift
      ;;
    --check)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Opción desconocida: $1"
      ;;
  esac
done

if [[ "$INSTALL_DEPS" == "1" ]]; then
  if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    log "Creando entorno virtual en .venv"
    python3 -m venv "$PROJECT_ROOT/.venv"
  fi
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
  log "Instalando dependencias Python"
  "$PYTHON_BIN" -m pip install -r "$PROJECT_ROOT/python_backend/requirements.txt"
fi

[[ -x "$PYTHON_BIN" ]] || fail "No encontré Python ejecutable en: $PYTHON_BIN. Probá: ./run.sh --install"

log "Usando Python: $PYTHON_BIN"
"$PYTHON_BIN" - <<'PY'
from python_backend.database.connection import get_database_path, initialize_database

initialize_database()
print(f"Base SQLite lista: {get_database_path()}")
PY

"$PYTHON_BIN" - <<'PY'
import importlib.util
import sys

missing = [name for name in ("fastapi", "uvicorn", "sqlalchemy", "pydantic", "httpx") if importlib.util.find_spec(name) is None]
if missing:
    print("Faltan dependencias: " + ", ".join(missing), file=sys.stderr)
    print("Ejecutá: ./run.sh --install", file=sys.stderr)
    raise SystemExit(1)
PY

if [[ "$RUN_PIPELINE" == "1" ]]; then
  log "Ejecutando pipeline Fase 2 -> Fase 3 -> Fase 4"
  "$PYTHON_BIN" - <<'PY'
from python_backend.services.duplicates.duplicates_service import process_trends_output
from python_backend.services.topic_selector.topic_selector_service import process_duplicates_output
from python_backend.services.trends.trends_service import save_trends_output
from tools.validate_output import validate_output_file

phase_2 = save_trends_output()
validate_output_file(phase_2)
print(f"Fase 2: {phase_2}")

phase_3 = process_trends_output(phase_2)
validate_output_file(phase_3)
print(f"Fase 3: {phase_3}")

phase_4 = process_duplicates_output(phase_3)
validate_output_file(phase_4)
print(f"Fase 4: {phase_4}")
PY
fi

if [[ "$CHECK_ONLY" == "1" ]]; then
  log "Chequeo OK. No levanto servidor porque usaste --check."
  exit 0
fi


assert_port_available() {
  local port="$1"
  local label="$2"
  "$PYTHON_BIN" - "$port" "$label" <<'PYCHECK'
import socket
import sys

port = int(sys.argv[1])
label = sys.argv[2]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    if sock.connect_ex(("127.0.0.1", port)) == 0:
        print(f"{label} no puede iniciar: el puerto {port} ya está en uso", file=sys.stderr)
        raise SystemExit(1)
PYCHECK
}

UVICORN_ARGS=("python_backend.main:app" "--host" "$HOST" "--port" "$PORT")
if [[ "$RELOAD" == "1" ]]; then
  UVICORN_ARGS+=("--reload")
fi

if [[ "$API_ONLY" == "1" ]]; then
  assert_port_available "$PORT" "FastAPI"
  log "Levantando sólo FastAPI en http://$HOST:$PORT"
  log "Cortá con Ctrl+C"
  exec "$PYTHON_BIN" -m uvicorn "${UVICORN_ARGS[@]}"
fi

[[ -f "$PROJECT_ROOT/frontend/index.html" ]] || fail "No encontré frontend/index.html. Primero generá o copiá la UI."
assert_port_available "$PORT" "FastAPI"
assert_port_available "$FRONTEND_PORT" "UI web"

cleanup() {
  local exit_code=$?
  log "Bajando servicios de desarrollo"
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" 2>/dev/null || true
  fi
  if [[ -n "${WEB_PID:-}" ]]; then
    kill "$WEB_PID" 2>/dev/null || true
  fi
  wait "$API_PID" 2>/dev/null || true
  wait "$WEB_PID" 2>/dev/null || true
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

log "Levantando FastAPI en http://$HOST:$PORT"
"$PYTHON_BIN" -m uvicorn "${UVICORN_ARGS[@]}" &
API_PID=$!

log "Levantando UI web en http://127.0.0.1:$FRONTEND_PORT"
"$PYTHON_BIN" -m http.server "$FRONTEND_PORT" --bind 127.0.0.1 --directory "$PROJECT_ROOT/frontend" &
WEB_PID=$!

log "API docs: http://$HOST:$PORT/docs"
log "UI: http://127.0.0.1:$FRONTEND_PORT"
log "Cortá ambos con Ctrl+C"
wait "$API_PID" "$WEB_PID"
