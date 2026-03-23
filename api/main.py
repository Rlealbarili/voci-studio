import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from celery.result import AsyncResult
from api.worker import celery_app, convert_audio_task, mix_audio_task
from api.database import get_db
from api.database import get_db
from api.models import InferenceHistory
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

app = FastAPI(title="Voci-Studio SaaS API", description="SaaS API for RVC inference powered by Celery")

@app.on_event("startup")
def on_startup():
    pass

class ConvertRequest(BaseModel):
    input_url: str
    model_name: str
    pitch: int = 0

class MixRequest(BaseModel):
    solo_url: str
    crowd_urls: List[str]
    pause_ms: int = 500
    stagger_ms: int = 200

@app.post("/api/v1/convert", status_code=202)
def convert_audio_endpoint(req: ConvertRequest, db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    
    # Save to InferenceHistory BEFORE dispatching to guarantee transactional integrity
    db_history = InferenceHistory(
        task_id=task_id,
        task_type="convert",
        status="PENDING",
        started_at=None
    )
    db.add(db_history)
    db.commit()
    
    try:
        task = convert_audio_task.apply_async(
            task_id=task_id,
            kwargs={
                "input_url": req.input_url,
                "model_name": req.model_name,
                "pitch": req.pitch
            }
        )
    except Exception as e:
        db_history.status = "FAILURE"
        db_history.error_text = f"Falha de broker Celery: {str(e)}"
        db.commit()
        raise HTTPException(status_code=503, detail="Broker de processamento indisponível.")
        
    return {"message": "Conversão iniciada", "task_id": task_id}

@app.post("/api/v1/mix", status_code=202)
def mix_audio_endpoint(req: MixRequest, db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    
    # Save to InferenceHistory BEFORE dispatching
    db_history = InferenceHistory(
        task_id=task_id,
        task_type="mix",
        status="PENDING",
        started_at=None
    )
    db.add(db_history)
    db.commit()
    
    try:
        task = mix_audio_task.apply_async(
            task_id=task_id,
            kwargs={
                "solo_url": req.solo_url,
                "crowd_urls": req.crowd_urls,
                "pause_ms": req.pause_ms,
                "stagger_ms": req.stagger_ms
            }
        )
    except Exception as e:
        db_history.status = "FAILURE"
        db_history.error_text = f"Falha de broker Celery: {str(e)}"
        db.commit()
        raise HTTPException(status_code=503, detail="Broker de processamento indisponível.")
        
    return {"message": "Mixagem iniciada", "task_id": task_id}

@app.get("/api/v1/status/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task_result = AsyncResult(task_id, app=celery_app)
    
    # Se o TTL no Redis expirou, o estado volta como PENDING (padrão)
    if task_result.state == "PENDING":
        db_history = db.query(InferenceHistory).filter(InferenceHistory.task_id == task_id).first()
        if db_history and db_history.status != "PENDING":
            response = {"task_id": task_id, "status": db_history.status}
            if db_history.status == "SUCCESS":
                response["result_url"] = db_history.output_url
            elif db_history.status == "FAILURE":
                response["error"] = db_history.error_text
            return response
    
    response = {
        "task_id": task_id,
        "status": task_result.status
    }
    
    if task_result.state == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.state == "FAILURE":
        response["error"] = str(task_result.info)
    elif task_result.state in ["DOWNLOADING", "CONVERTING", "MIXING", "UPLOADING"]:
        response["progress_info"] = task_result.info
        
    return response

# Serve static files for mock downloading (simulating S3)
from fastapi.staticfiles import StaticFiles
import os
os.makedirs("static/results", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
