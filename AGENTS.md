# AGENTS.md - Voci-Studio

## 1. Project Context
Welcome to **Voci-Studio**, an autonomous AI voice conversion and mixing SaaS. 
This project is an API-first application built with **FastAPI**, **Celery**, **Redis**, and **PostgreSQL**.
It is designed to be highly scalable, dispatching heavy GPU audio processing (using the RVC engine - Applio) to background workers.

## 2. Dev Environment Tips
- The environment uses Python 3.10 with a `venv` located at the root. Always source it: `source venv/bin/activate`.
- Environment variables are managed via `python-dotenv`. An example is available in `.env.example`.
- **CRITICAL:** Do NOT attempt to install OS-level dependencies via `apt-get` or modify other COGEP stacks, as this project runs in parallel on an enterprise server (IRON-SERVER). Use the integrated Docker instances (`cogep-redis`, `cogep-postgres`) passing specific DB/Keys (e.g., Redis index `/2`, DB `voci_db`).
- GPU Workloads are highly strictly orchestrated: use `CUDA_VISIBLE_DEVICES` explicitly. `start_workers.sh` uses GPU 0 for Worker 1 and GPU 1 for Worker 2 to avoid resource starving. No other systems should be impacted by our inference.

## 3. Architecture & Guidelines
- **API (FastAPI):** Must be fully async and return HTTP `202 Accepted` immediately upon receiving audio requests. Avoid synchronous GPU calls in the API layer.
- **Workers (Celery):** Located in `api/worker.py`. They consume URLs from S3/MinIO, download, process via `core.converter.VoiceConverter` and upload back.
- **Storage:** Hard disks shouldn't be overwhelmed. Everything must rely on temporary `/tmp` paths that are explicitly cleaned up in `finally` blocks inside the Tasks.
- **Database:** SQLAlchemy ORM models (`api/models.py`). Manage User balances and inference costs carefully.

## 4. Execution & Testing
- To run the application stack: `./start_workers.sh`. It starts Uvicorn and 2 Celery workers.
- To monitor real-time execution, read the logs in `logs/worker_gpu0.log`, `logs/worker_gpu1.log`, and `logs/api.log`.
- Any code generated must respect typing hints (`typing`) and structure.

## 5. Next Focus (Current Roadmap)
We are currently focusing on UI/UX, MinIO/S3 Storage implementation, Keycloak Authentication enforcement, and User Credits handling. Agents interacting with this repo must read the `docs/` folder to understand the specific milestones.
