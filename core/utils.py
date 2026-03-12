"""
core/utils.py — Utilitários de áudio compartilhados por todo o framework.
"""

import numpy as np
import soundfile as sf
from pydub import AudioSegment
from pedalboard import Pedalboard, Reverb


def load_mono(path: str) -> tuple[np.ndarray, int]:
    """Carrega WAV e converte para mono float32."""
    audio, sr = sf.read(str(path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float32), sr


def normalize(audio: np.ndarray, peak: float = 0.95) -> np.ndarray:
    """Normaliza para pico máximo definido."""
    m = np.max(np.abs(audio))
    if m > 0:
        audio = audio / m * peak
    return audio


def apply_reverb(
    audio: np.ndarray,
    sr: int,
    room_size: float = 0.25,
    damping: float = 0.55,
    wet_level: float = 0.08,
    dry_level: float = 0.92,
) -> np.ndarray:
    """Aplica reverb via pedalboard."""
    board = Pedalboard([Reverb(
        room_size=room_size,
        damping=damping,
        wet_level=wet_level,
        dry_level=dry_level,
    )])
    return board(audio, sr)


def to_pydub(audio: np.ndarray, sr: int, target_sr: int = 44100) -> AudioSegment:
    """Converte numpy float32 para AudioSegment pydub, upsampleando se necessário."""
    audio = normalize(audio)
    i16 = np.int16(audio * 32767)
    seg = AudioSegment(i16.tobytes(), frame_rate=sr, sample_width=2, channels=1)
    if sr != target_sr:
        seg = seg.set_frame_rate(target_sr)
    return seg
