#!/bin/bash
# setup/start_webui.sh — Inicia Applio WebUI na GPU 1 (porta 7897)
#
# Acesso local:           http://localhost:7897
# Acesso remoto (tunnel): ssh -L 7897:localhost:7897 usuario@servidor

BASE=/opt/cogep-lab/data/RVC
export CUDA_VISIBLE_DEVICES=1

echo "Iniciando Applio WebUI..."
echo "Acesse: http://localhost:7897"
echo "Tunnel: ssh -L 7897:localhost:7897 $(whoami)@$(hostname -I | awk '{print $1}')"
echo ""

cd $BASE/Applio
env/bin/python app.py --port 7897 --listen 2>&1 | tee $BASE/applio_webui.log
