"""
core/mixer.py — Motor de composição multi-voz.

Responsabilidade: receber WAVs já convertidos (solo + lista de crowd)
e montar a composição final com timing, reverb e cascata.
"""

import pathlib
import numpy as np
import librosa
from pydub import AudioSegment

from core.utils import load_mono, normalize, apply_reverb, to_pydub


def process_solo(
    wav_path: pathlib.Path,
    reverb: dict,
    output_sr: int = 44100,
) -> AudioSegment:
    """Carrega, normaliza e aplica reverb leve no solo."""
    audio, sr = load_mono(wav_path)
    audio = normalize(audio, 0.98)
    audio = apply_reverb(audio, sr, **reverb)
    audio = normalize(audio, 0.97)
    return to_pydub(audio, sr, output_sr)


def process_crowd_voice(
    wav_path: pathlib.Path,
    pitch_fine: float,
    reverb_wet: float,
    crowd_room: float,
    crowd_damp: float,
    output_sr: int = 44100,
) -> AudioSegment:
    """
    Processa uma voz da multidão:
    micro pitch-shift + reverb ambiental.

    Args:
        pitch_fine:  Variação de pitch em semitons (ex: +0.8, -0.5).
                     Pequenas variações criam sensação de vozes distintas.
        reverb_wet:  Nível de reverb (0.0–1.0). Vozes mais ao fundo = mais wet.
    """
    audio, sr = load_mono(wav_path)

    if abs(pitch_fine) > 0.05:
        audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=pitch_fine)

    audio = normalize(audio, 0.95)
    audio = apply_reverb(
        audio, sr,
        room_size=crowd_room,
        damping=crowd_damp,
        wet_level=reverb_wet,
        dry_level=1.0 - reverb_wet,
    )
    audio = normalize(audio, 0.92)
    return to_pydub(audio, sr, output_sr)


def compose(
    solo_seg: AudioSegment,
    crowd_segs: list[AudioSegment],
    pause_ms: int,
    stagger_ms: int,
    output_sr: int = 44100,
) -> AudioSegment:
    """
    Monta composição final: solo → pausa → cascata de vozes.

    A cascata entra com `stagger_ms` de delay entre cada voz,
    criando o efeito de coro chegando em ondas sucessivas.

    Args:
        solo_seg:    Segmento do grito solo.
        crowd_segs:  Lista de segmentos da multidão.
        pause_ms:    Silêncio entre solo e multidão (ms).
        stagger_ms:  Delay entre cada voz da cascata (ms).

    Returns:
        AudioSegment com a composição completa.
    """
    base = solo_seg + AudioSegment.silent(duration=pause_ms, frame_rate=output_sr)
    crowd_start = len(base)

    # Pré-calcular duração total para evitar truncamento no overlay
    last_start = crowd_start + (len(crowd_segs) - 1) * stagger_ms
    max_crowd  = max(len(s) for s in crowd_segs)
    total_ms   = last_start + max_crowd + 300  # margem de segurança

    if len(base) < total_ms:
        base = base + AudioSegment.silent(
            duration=total_ms - len(base),
            frame_rate=output_sr,
        )

    final = base
    for i, seg in enumerate(crowd_segs):
        pos = crowd_start + i * stagger_ms
        final = final.overlay(seg, position=pos)

    return final
