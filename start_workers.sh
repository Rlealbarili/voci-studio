#!/bin/bash
# start_workers.sh - Orquestração do SaaS Voci-Studio
# Inicia 2 Celery Workers (cada um preso a uma GPU) e a API Uvicorn.

echo "Iniciando orquestração do Voci-Studio SaaS..."

# Certificar que o ambiente virtual está ativado
if [ -z "$VIRTUAL_ENV" ]; then
    source venv/bin/activate
fi

# Cria o arquivo de logs e diretório temporário
mkdir -p logs
mkdir -p static/results

# Inicia o Redis local (caso seja necessário o comando background do SO via Docker ou sudo service)
# Nota: Configurado no prompt para assumir Redis na mesma máquina.
# Se Redis já estiver rodando, essa linha pode ser ajustada.
# docker run -d --name voci-redis -p 6379:6379 redis:alpine 2>/dev/null

echo "Iniciando Worker 1 na GPU 0..."
CUDA_VISIBLE_DEVICES=0 celery -A api.worker worker --loglevel=info -n worker_gpu0@%h -c 1 > logs/worker_gpu0.log 2>&1 &
WORKER1_PID=$!

echo "Iniciando Worker 2 na GPU 1..."
CUDA_VISIBLE_DEVICES=1 celery -A api.worker worker --loglevel=info -n worker_gpu1@%h -c 1 > logs/worker_gpu1.log 2>&1 &
WORKER2_PID=$!

echo "Iniciando API FastAPI na porta 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
API_PID=$!

echo "Todos os serviços foram iniciados no background."
echo "Worker 1 PID: $WORKER1_PID"
echo "Worker 2 PID: $WORKER2_PID"
echo "API Server PID: $API_PID"

echo "Use 'tail -f logs/*.log' para monitorar."
echo "Para parar os serviços, execute: kill $WORKER1_PID $WORKER2_PID $API_PID"

# Aguardando para manter o shell script rodando na foreground (opcional)
wait $API_PID
