#!/usr/bin/env bash
# Audio bidireccional half-duplex con GStreamer + Opus por UDP (prueba "2-way audio" del reglamento).
#   En el robot:     ./audio_ptt.sh robot <IP_OPERADOR>
#   En la notebook:  ./audio_ptt.sh operador <IP_ROBOT>      (Enter = hablar, Enter = soltar, q = salir)
# Requiere: sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-{base,good,bad} gstreamer1.0-pulseaudio
set -euo pipefail
ROL=${1:?uso: $0 robot|operador IP_DESTINO}
DEST=${2:?falta IP destino}
AMBIENTE_PORT=5002     # robot -> operador (siempre abierto)
VOZ_PORT=5003          # operador -> robot (solo mientras se habla)
CAPS='application/x-rtp,media=audio,encoding-name=OPUS,payload=96,clock-rate=48000'

if [[ "$ROL" == "robot" ]]; then
  echo "[robot] enviando ambiente a $DEST:$AMBIENTE_PORT y escuchando voz en :$VOZ_PORT"
  gst-launch-1.0 -q autoaudiosrc ! audioconvert ! audioresample ! opusenc bitrate=24000 ! rtpopuspay ! \
    udpsink host="$DEST" port=$AMBIENTE_PORT &
  SEND=$!
  trap 'kill $SEND 2>/dev/null' EXIT
  gst-launch-1.0 -q udpsrc port=$VOZ_PORT caps="$CAPS" ! rtpjitterbuffer latency=60 ! rtpopusdepay ! \
    opusdec ! audioconvert ! volume volume=2.0 ! autoaudiosink
elif [[ "$ROL" == "operador" ]]; then
  echo "[operador] escuchando ambiente del robot (:$AMBIENTE_PORT). Enter = HABLAR / Enter = soltar, q = salir"
  gst-launch-1.0 -q udpsrc port=$AMBIENTE_PORT caps="$CAPS" ! rtpjitterbuffer latency=60 ! rtpopusdepay ! \
    opusdec ! audioconvert ! autoaudiosink &
  RECV=$!
  trap 'kill $RECV 2>/dev/null; [[ -n "${TALK:-}" ]] && kill $TALK 2>/dev/null' EXIT
  TALK=""
  while read -r -p "> " k; do
    [[ "$k" == "q" ]] && break
    if [[ -z "$TALK" ]]; then
      gst-launch-1.0 -q autoaudiosrc ! audioconvert ! audioresample ! opusenc bitrate=24000 ! rtpopuspay ! \
        udpsink host="$DEST" port=$VOZ_PORT &
      TALK=$!; echo "  ** HABLANDO ** (Enter para soltar)"
    else
      kill $TALK; TALK=""; echo "  (escuchando)"
    fi
  done
else
  echo "rol desconocido: $ROL"; exit 1
fi
