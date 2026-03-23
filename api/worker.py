import os
from dotenv import load_dotenv

load_dotenv()
import time
import urllib.request
from urllib.parse import urlparse
from datetime import datetime
from celery import Celery
from api.database import SessionLocal
from api.models import InferenceHistory
import pathlib
from core.converter import VoiceConverter
from core.mixer import process_solo, process_crowd_voice, compose

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/2")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/3")

celery_app = Celery(
    "voci_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=5,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,
    task_time_limit=1800,
    task_soft_time_limit=1500
)

# Initialize the converter globally per worker process
converter = None

def get_converter():
    global converter
    if converter is None:
        converter = VoiceConverter()
    return converter

def update_task_db(task_id: str, status: str, error_text: str = None, output_url: str = None):
    db = SessionLocal()
    try:
        history = db.query(InferenceHistory).filter(InferenceHistory.task_id == task_id).first()
        if history:
            history.status = status
            history.gpu_id = os.environ.get("CUDA_VISIBLE_DEVICES", "0")
            if status in ["CONVERTING", "MIXING"]:
                if not history.started_at:
                    history.started_at = datetime.utcnow()
            if status in ["SUCCESS", "FAILURE"]:
                history.finished_at = datetime.utcnow()
                if history.started_at:
                    sec = (history.finished_at - history.started_at).total_seconds()
                    history.duration_seconds = sec
                    history.cost_deducted = sec * 0.5
            if error_text:
                history.error_text = error_text
            if output_url:
                history.output_url = output_url
            db.commit()
    except Exception as e:
        print(f"Error updating DB: {e}")
    finally:
        db.close()

def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]: return False
        host = parsed.hostname
        if not host: return False
        # Bloquear metadados em nuvem e localhost hardcoded
        if host in ["169.254.169.254", "localhost", "127.0.0.1", "0.0.0.0"]:
            return False
        return True
    except:
        return False

def download_file(url: str, dest_path: str):
    if not is_safe_url(url) and (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"SSRF Security: Host bloqueado para download ({url})")
    
    if url.startswith("http://") or url.startswith("https://"):
        req = urllib.request.Request(url, headers={'User-Agent': 'Voci-Studio/1.0'})
        with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, 'wb') as out_file:
            import shutil
            shutil.copyfileobj(response, out_file)
    else:
        # Prevent Path traversal
        safe_path = os.path.abspath(url)
        if not safe_path.startswith('/tmp/'): # Fallback para segurança de inputs locais da propria api
             raise ValueError("Path not allowed.")
        import shutil
        shutil.copy(safe_path, dest_path)

@celery_app.task(bind=True)
def convert_audio_task(self, input_url: str, model_name: str, pitch: int = 0):
    """
    Downloads audio, runs VoiceConverter, and 'uploads' (or saves) result.
    """
    # Create temp paths
    temp_dir = pathlib.Path("/tmp/voci_tasks") / self.request.id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    input_path = temp_dir / "input.wav"
    output_path = temp_dir / "output.wav"
    
    try:
        self.update_state(state='DOWNLOADING', meta={'progress': 10})
        update_task_db(self.request.id, 'DOWNLOADING')
        
        download_file(input_url, str(input_path))
        
        self.update_state(state='CONVERTING', meta={'progress': 30})
        update_task_db(self.request.id, 'CONVERTING')
        conv = get_converter()
        
        # Determine model path
        model_name = os.path.basename(model_name) # Saneamento SSRF / Traversal
        models_dir_env = os.environ.get("MODELS_DIR", "./models")
        models_dir = pathlib.Path(models_dir_env)
        from core.converter import find_model_files
        try:
            model_pth, model_index = find_model_files(models_dir, model_name)
        except Exception as e:
            # Fallback path if find_model_files fails or models not structured correctly
            model_pth = models_dir / f"{model_name}.pth"
            model_index = None

        device = f"cuda:{os.environ.get('CUDA_VISIBLE_DEVICES', '0')}"

        success = conv.convert(
            input_path=str(input_path),
            output_path=str(output_path),
            model_pth=str(model_pth),
            model_index=str(model_index) if model_index else None,
            pitch=pitch,
            device=device
        )
        
        if not success:
            raise Exception("Conversão falhou (arquivo vazio ou erro no Applio).")

        self.update_state(state='UPLOADING', meta={'progress': 90})
        update_task_db(self.request.id, 'UPLOADING')
        
        # TODO: Implement upload to S3 here. For now, we simulate returning the local path.
        final_url = f"/static/results/{self.request.id}_output.wav"
        
        # Simulate moving to a static dir accessible by API
        static_dir = pathlib.Path(os.path.abspath("./static/results"))
        static_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        out_path_abs = static_dir / f"{self.request.id}_output.wav"
        shutil.copy(str(output_path), str(out_path_abs))

        update_task_db(self.request.id, 'SUCCESS', output_url=final_url)
        return {"status": "success", "result_url": final_url}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        update_task_db(self.request.id, 'FAILURE', error_text=str(e))
        raise e
    finally:
        # Cleanup
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

@celery_app.task(bind=True)
def mix_audio_task(self, solo_url: str, crowd_urls: list, pause_ms: int = 500, stagger_ms: int = 200):
    """
    Downloads converted audios and runs Mixer.
    """
    temp_dir = pathlib.Path("/tmp/voci_tasks") / self.request.id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    solo_path = temp_dir / "solo.wav"
    out_path = temp_dir / "mix_output.wav"
    
    try:
        self.update_state(state='DOWNLOADING', meta={'progress': 10})
        update_task_db(self.request.id, 'DOWNLOADING')
        download_file(solo_url, str(solo_path))
        
        crowd_paths = []
        for idx, url in enumerate(crowd_urls):
            c_path = temp_dir / f"crowd_{idx}.wav"
            download_file(url, str(c_path))
            crowd_paths.append(c_path)
            
        self.update_state(state='MIXING', meta={'progress': 50})
        update_task_db(self.request.id, 'MIXING')
        
        # Process solo with default reverb
        reverb_params = {"room_size": 0.8, "damping": 1.0, "wet_level": 0.15, "dry_level": 0.9}
        solo_seg = process_solo(solo_path, reverb_params)
        
        crowd_segs = []
        for i, c_path in enumerate(crowd_paths):
            # Vary pitch and reverb slightly for each crowd voice
            pitch_fine = (i % 3 - 1) * 0.5  # -0.5, 0.0, 0.5
            reverb_wet = 0.2 + (i * 0.05)
            c_seg = process_crowd_voice(c_path, pitch_fine, reverb_wet, crowd_room=0.9, crowd_damp=0.5)
            crowd_segs.append(c_seg)
            
        final_mix = compose(solo_seg, crowd_segs, pause_ms, stagger_ms)
        final_mix.export(str(out_path), format="wav")

        self.update_state(state='UPLOADING', meta={'progress': 90})
        update_task_db(self.request.id, 'UPLOADING')
        
        final_url = f"/static/results/{self.request.id}_mix.wav"
        static_dir = pathlib.Path(os.path.abspath("./static/results"))
        static_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        out_path_abs = static_dir / f"{self.request.id}_mix.wav"
        shutil.copy(str(out_path), str(out_path_abs))

        update_task_db(self.request.id, 'SUCCESS', output_url=final_url)
        return {"status": "success", "result_url": final_url}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        update_task_db(self.request.id, 'FAILURE', error_text=str(e))
        raise e
    finally:
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
