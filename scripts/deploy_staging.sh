#!/usr/bin/env bash
# ============================================================
# Despliegue del Reloj Checador al VPS de STAGING (valexpress-staging)
# ============================================================
# Idempotente: correrlo dos veces no deja el servidor a medias ni duplica nada.
# No toca la base de datos ni los volumenes; solo sincroniza codigo, reconstruye
# las imagenes y recrea los contenedores cuya imagen cambio.
#
#   ./scripts/deploy_staging.sh
#
# Requisitos, comprobados antes de empezar:
#   - alias `valexpress-staging` en ~/.ssh/config (la llave vive en la boveda
#     cifrada: `boveda abrir` antes de correr esto)
#   - .env.staging YA creado en el servidor, en $DESTINO (ver .env.staging.example).
#     No se copia desde la laptop a proposito: los secretos no viajan en cada
#     despliegue ni quedan en el historial de la terminal.
# ============================================================
set -euo pipefail

HOST="${CHECADOR_HOST:-valexpress-staging}"
DESTINO="${CHECADOR_DESTINO:-/root/checador-staging}"
COMPOSE="docker-compose.staging.yml"
PROYECTO="checador-staging"

cd "$(dirname "$0")/.."

echo "==> 1/5  Comprobando acceso a $HOST"
ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" true || {
  echo "ERROR: no hay acceso SSH a $HOST." >&2
  echo "       Si la llave esta en la boveda cifrada: 'boveda abrir' y reintenta." >&2
  exit 1
}

echo "==> 2/5  Comprobando que existe .env.staging en el servidor"
# Se comprueba ANTES de sincronizar: sin el, el compose aborta a mitad del
# despliegue y deja el codigo nuevo con los contenedores viejos.
if ! ssh "$HOST" "test -f $DESTINO/.env.staging"; then
  echo "ERROR: falta $DESTINO/.env.staging en el servidor." >&2
  echo "       Crearlo una sola vez:" >&2
  echo "         ssh $HOST" >&2
  echo "         mkdir -p $DESTINO && cd $DESTINO" >&2
  echo "         # copiar .env.staging.example y rellenar las contrasenas" >&2
  echo "         openssl rand -base64 24" >&2
  exit 1
fi

echo "==> 3/5  Sincronizando codigo"
# --delete mantiene el servidor igual al repo, pero se excluye .env.staging para
# no borrar los secretos que viven solo ahi, y data/ por si alguna vez se uso.
rsync -az --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'data' \
  --exclude '__pycache__' \
  --exclude 'frontend/dist' \
  --exclude 'legacy' \
  --exclude '.env.staging' \
  ./ "$HOST:$DESTINO/"

echo "==> 4/5  Construyendo y levantando (build ~1m30s con 1 CPU)"
ssh "$HOST" "cd $DESTINO && docker compose -f $COMPOSE --env-file .env.staging -p $PROYECTO up -d --build"

echo "==> 5/5  Comprobando que responde"
# Los puertos se leen del .env del servidor, no se asumen: si alguien los cambio
# ahi, esta comprobacion debe seguir apuntando al lugar correcto.
ssh "$HOST" "cd $DESTINO && set -a && . ./.env.staging && set +a && \
  for i in \$(seq 1 20); do
    if curl -sf -m 5 \"http://127.0.0.1:\${BACKEND_PORT:-8001}/health\" >/dev/null; then
      echo 'backend  OK'
      curl -sf -m 5 -o /dev/null \"http://127.0.0.1:\${FRONTEND_PORT:-8085}/\" && echo 'frontend OK'
      exit 0
    fi
    sleep 3
  done
  echo 'ERROR: el backend no respondio tras 60s. Logs:' >&2
  docker logs --tail 40 checador_staging_backend >&2
  exit 1"

echo
echo "Listo. Comprobar tambien desde fuera:"
echo "  https://checador.staging.valeexpress.mx"
