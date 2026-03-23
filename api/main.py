import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from celery.result import AsyncResult
from api.worker import celery_app, convert_audio_task, mix_audio_task
from api.database import init_db

app = FastAPI(title="Voci-Studio SaaS API", description="SaaS API for RVC inference powered by Celery")

@app.on_event("startup")
def on_startup():
    init_db()

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
def convert_audio_endpoint(req: ConvertRequest):
    task = convert_audio_task.delay(
        input_url=req.input_url,
        model_name=req.model_name,
        pitch=req.pitch
    )
    return {"message": "Conversão iniciada", "task_id": task.id}

@app.post("/api/v1/mix", status_code=202)
def mix_audio_endpoint(req: MixRequest):
    task = mix_audio_task.delay(
        solo_url=req.solo_url,
        crowd_urls=req.crowd_urls,
        pause_ms=req.pause_ms,
        stagger_ms=req.stagger_ms
    )
    return {"message": "Mixagem iniciada", "task_id": task.id}

@app.get("/api/v1/status/{task_id}")
def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
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
