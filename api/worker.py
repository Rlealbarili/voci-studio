import os
import time
import urllib.request
from celery import Celery
import pathlib
from core.converter import VoiceConverter
from core.mixer import process_solo, process_crowd_voice, compose

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

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
    worker_prefetch_multiplier=1, # 1 task per worker at a time for GPU
)

# Initialize the converter globally per worker process
converter = None

def get_converter():
    global converter
    if converter is None:
        converter = VoiceConverter()
    return converter

def download_file(url: str, dest_path: str):
    if url.startswith("http://") or url.startswith("https://"):
        urllib.request.urlretrieve(url, dest_path)
    else:
        # Assume it's a local path or already mounted
        import shutil
        shutil.copy(url, dest_path)

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
        download_file(input_url, str(input_path))
        
        self.update_state(state='CONVERTING', meta={'progress': 30})
        conv = get_converter()
        
        # Determine model path (pseudo-code, you need to point to your models directory)
        models_dir = pathlib.Path("./models")
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
        # TODO: Implement upload to S3 here. For now, we simulate returning the local path.
        final_url = f"/static/results/{self.request.id}_output.wav"
        
        # Simulate moving to a static dir accessible by API
        static_dir = pathlib.Path("./static/results")
        static_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(str(output_path), str(static_dir / f"{self.request.id}_output.wav"))

        return {"status": "success", "result_url": final_url}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
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
        download_file(solo_url, str(solo_path))
        
        crowd_paths = []
        for idx, url in enumerate(crowd_urls):
            c_path = temp_dir / f"crowd_{idx}.wav"
            download_file(url, str(c_path))
            crowd_paths.append(c_path)
            
        self.update_state(state='MIXING', meta={'progress': 50})
        
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
        
        final_url = f"/static/results/{self.request.id}_mix.wav"
        static_dir = pathlib.Path("./static/results")
        static_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(str(out_path), str(static_dir / f"{self.request.id}_mix.wav"))

        return {"status": "success", "result_url": final_url}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise e
    finally:
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
