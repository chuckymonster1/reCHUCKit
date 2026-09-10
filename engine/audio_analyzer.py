"""Audio-reference analysis for reCHUCKit.

This module extracts stable, inspectable features used to judge MIDI against a
stem. It deliberately separates *measurement* from *correction*: low-confidence
measurements must never silently rewrite musical material.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import librosa
import numpy as np


@dataclass(frozen=True)
class AudioFeatures:
    file: str
    sample_rate: int
    duration_seconds: float
    tempo_bpm: float
    onset_times: list[float]
    pitch_classes: list[float]
    rms_mean: float


def analyze_audio(path: str | Path, sample_rate: int = 44100) -> AudioFeatures:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    y, sr = librosa.load(path, sr=sample_rate, mono=True)
    if y.size == 0:
        raise ValueError(f"Audio file contains no samples: {path}")

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_value = float(np.asarray(tempo).reshape(-1)[0])
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    total = float(chroma_mean.sum())
    pitch_classes = (chroma_mean / total).tolist() if total > 0 else [0.0] * 12
    rms = librosa.feature.rms(y=y)

    return AudioFeatures(
        file=str(path),
        sample_rate=sr,
        duration_seconds=round(float(librosa.get_duration(y=y, sr=sr)), 4),
        tempo_bpm=round(tempo_value, 3),
        onset_times=[round(float(v), 5) for v in onset_times],
        pitch_classes=[round(float(v), 6) for v in pitch_classes],
        rms_mean=round(float(rms.mean()), 6),
    )


def to_dict(features: AudioFeatures) -> dict:
    return asdict(features)
