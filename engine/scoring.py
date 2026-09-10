"""Transparent structural scoring for reCHUCKit.

This is not a timbre/sound-alike score. It measures only evidence we can defend
from reference audio and MIDI: tempo agreement, pitch-class similarity and onset
coverage. The report exposes every component instead of hiding a magic number.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from engine.alignment import midi_note_on_times
from engine.audio_analyzer import AudioFeatures
from engine.pitch_engine import midi_pitch_histogram


@dataclass(frozen=True)
class StructuralScore:
    score: float
    confidence: float
    tempo_score: float
    pitch_score: float
    onset_score: float
    label: str
    limitations: str


def _cosine(a: list[float], b: list[float]) -> float:
    av = np.asarray(a, dtype=float)
    bv = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, float(np.dot(av, bv) / denom)))


def _cluster_onsets(times: list[float], tolerance: float = 0.035) -> list[float]:
    if not times:
        return []
    ordered = sorted(times)
    groups: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - groups[-1][-1] <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [sum(group) / len(group) for group in groups]


def _onset_coverage(midi_times: list[float], audio_times: list[float], tolerance: float = 0.09) -> float:
    midi = _cluster_onsets(midi_times)
    if not midi or not audio_times:
        return 0.0
    audio = np.asarray(audio_times, dtype=float)
    matches = sum(1 for value in midi if float(np.min(np.abs(audio - value))) <= tolerance)
    return matches / len(midi)


def score_structure(reference: AudioFeatures, midi_path: str | Path) -> StructuralScore:
    midi_hist = midi_pitch_histogram(midi_path)
    midi_onsets = midi_note_on_times(midi_path)

    # Tempo is useful but octave/double-time ambiguity is common in beat trackers.
    from engine.midi_engine import analyze

    midi_tempo = analyze(midi_path).tempo_bpm
    candidates = [midi_tempo, midi_tempo * 2, midi_tempo / 2]
    tempo_error = min(abs(reference.tempo_bpm - candidate) for candidate in candidates)
    tempo_score = max(0.0, 1.0 - tempo_error / max(12.0, reference.tempo_bpm * 0.16))
    pitch_score = _cosine(reference.pitch_classes, midi_hist)
    onset_score = _onset_coverage(midi_onsets, reference.onset_times)

    weighted = 0.25 * tempo_score + 0.45 * pitch_score + 0.30 * onset_score
    evidence = sum(
        (
            1 if reference.tempo_bpm > 0 else 0,
            1 if max(reference.pitch_classes, default=0) > 0 and max(midi_hist, default=0) > 0 else 0,
            1 if reference.onset_times and midi_onsets else 0,
        )
    )
    confidence = evidence / 3
    label = "strong structural match" if weighted >= 0.8 else "partial structural match" if weighted >= 0.55 else "weak structural match"

    return StructuralScore(
        score=round(weighted * 100, 1),
        confidence=round(confidence, 3),
        tempo_score=round(tempo_score * 100, 1),
        pitch_score=round(pitch_score * 100, 1),
        onset_score=round(onset_score * 100, 1),
        label=label,
        limitations="Structural only; does not measure instrument tone, mix, effects, articulation or vocal identity.",
    )


def to_dict(result: StructuralScore) -> dict:
    return asdict(result)
