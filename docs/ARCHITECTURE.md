# Visão Geral da Arquitetura Voci-Studio

O Voci-Studio é uma aplicação moderna do tipo SaaS orientada a eventos para inferência densa de inteligência artificial (Conversão de Voz).

## Componentes do Sistema

### 1. API Gateway e Roteamento (FastAPI)
- **Localização:** `api/main.py`
- É a porta de entrada. Recebe os payloads JSON (URLs de áudios, modelo, pitch).
- Imediatamente enfileira a requisição pelo Celery via Redis e devolve um `task_id`.
- Fornece um endpoint de polling `/api/v1/status/{task_id}` para os clientes acompanharem o status do processamento ('DOWNLOADING', 'CONVERTING', etc.).

### 2. Mensageria e Fila (Redis + Celery)
- **Localização:** `api/worker.py`
- Utiliza a instância COGEP Redis disponível em `localhost:6379`.
- Isolada utilizando os índices da base de dados `/2` (Broker) e `/3` (Result Backend).

### 3. Workers Isolados de GPU
A arquitetura levanta múltiplos processos independentes.
Para proteger os recursos físicos do servidor (IRON-SERVER) e os aplicativos adjacentes:
- **Worker 0:** Escuta as tarefas amarrado unicamente à **GPU 0** (`CUDA_VISIBLE_DEVICES=0`).
- **Worker 1:** Escuta as tarefas amarrado unicamente à **GPU 1** (`CUDA_VISIBLE_DEVICES=1`).
Ambos estão configurados com pré-busca (prefetch) limitados a 1 tarefa concorrente por processo, controlando o uso da VRAM Pytorch.

### 4. Banco de Dados e Faturamento
- **Localização:** `api/models.py` e `api/database.py`
- Usa PostgreSQL (`localhost:5432`, db: `voci_db`) gerenciado pelo SQLAlchemy.
- A auto-criação de tabelas é manipulada nativamente pelo evento `startup` da API.
- Destina-se ao armazenamento do histórico das inferências limitando os gastos do usuário.

### 5. Backend RVC e Modelos
- Encontra-se atrelado no ambiente COGEP (`MODELS_DIR` e `APPLIO_DIR`).
- A biblioteca modular do `VoiceConverter` carrega os pesos instantaneamente respeitando a alocação `cuda:0/1`.
