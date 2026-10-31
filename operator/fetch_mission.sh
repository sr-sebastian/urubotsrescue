#!/usr/bin/env bash
# Trae los archivos de la última misión del robot (GeoTIFF + PLY + CSV). Hay 5 minutos para entregarlos.
#   ./fetch_mission.sh [usuario@ip]      (por defecto carpincho@192.168.8.10)
set -euo pipefail
ROBOT=${1:-carpincho@192.168.8.10}
DEST=${2:-$HOME/entregas}
mkdir -p "$DEST"
ULTIMA=$(ssh "$ROBOT" 'ls -1d ~/carpincho_mission/*/ | tail -1')
echo "Copiando $ULTIMA ..."
scp -r "$ROBOT:$ULTIMA" "$DEST/"
ls -la "$DEST/$(basename "$ULTIMA")"
echo "Listo. Copiar a la memoria USB de los jueces SIN abrir ni editar los archivos."
