# Guia de Configuração (Setup) - Voci-Studio SaaS

Este guia descreve as etapas para configurar e rodar o Voci-Studio SaaS no servidor local (IRON-SERVER).

## 1. Pré-Requisitos

- O ambiente requer **Python 3.10+**.
- Instâncias do `cogep-redis` e `cogep-postgres` devem estar ativas e alcançáveis em `localhost` pelo Docker.
- O diretório de vozes (`MODELS_DIR`) e o repositório base do RVC (`APPLIO_DIR`) devem estar pré-instalados na máquina (no nosso caso, `/opt/cogep-lab/data/RVC/...`).

## 2. Preparação do Ambiente

```bash
# Clone o repositório
git clone https://github.com/Rlealbarili/voci-studio.git
cd voci-studio

# Crie e ative o ambiente virtual
python3.10 -m venv venv
source venv/bin/activate

# Instale o PyTorch (Otimizado para CUDA 12.1)
pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121

# Instale as dependências gerais
pip install -r requirements.txt
pip install fastapi uvicorn celery redis sqlalchemy psycopg2-binary python-dotenv pydantic python-multipart
```

## 3. Variáveis de Ambiente (.env)

Copie o `.env.example` para `.env` e preencha-o:
```bash
cp .env.example .env
```

Garanta que sua URI do banco e as portas do Redis apontem corretamente para isolamento:
```env
DATABASE_URL=postgresql://flowise:SENHA@localhost:5432/voci_db
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3
APPLIO_DIR=/opt/cogep-lab/data/RVC/Applio
MODELS_DIR=/opt/cogep-lab/data/RVC/models
```

## 4. Inicialização

Para subir os processos com orquestração isolada de GPU (Worker 1 na placa 0, Worker 2 na placa 1):
```bash
chmod +x start_workers.sh
./start_workers.sh
```

A base de dados será construída instantaneamente após abrir o servidor `uvicorn` na porta `8000`.
Acompanhe os logs localmente em `logs/*.log`.
