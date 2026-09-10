"""Pitch and chord comparison for reCHUCKit.

Uses audio chroma as a reference and MIDI note content as the editable source.
All corrections are confidence-scored proposals. Nothing is mutated here.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter
import mido
import numpy as np

PITCH_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

@dataclass(frozen=True)
class PitchComparison:
    midi_pitch_class: int
    midi_pitch_name: str
    audio_pitch_class: int
    audio_pitch_name: str
    semitone_delta: int
    confidence: float
    action: str


def midi_pitch_histogram(path: str | Path) -> list[float]:
    mid = mido.MidiFile(path)
    counts = Counter()
    total = 0
    for track in mid.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                counts[msg.note % 12] += 1
                total += 1
    if total == 0:
        return [0.0] * 12
    return [counts[i] / total for i in range(12)]


def dominant_pitch_class(histogram: list[float]) -> int | None:
    if not histogram or max(histogram) <= 0:
        return None
    return int(np.argmax(np.asarray(histogram, dtype=float)))


def compare_pitch_centers(midi_histogram: list[float], audio_pitch_classes: list[float],
                          auto_threshold: float = 0.92) -> PitchComparison | None:
    if len(midi_histogram) != 12 or len(audio_pitch_classes) != 12:
        raise ValueError("Pitch-class histograms must each contain 12 values")
    midi_pc = dominant_pitch_class(midi_histogram)
    audio_pc = dominant_pitch_class(audio_pitch_classes)
    if midi_pc is None or audio_pc is None:
        return None

    delta = (audio_pc - midi_pc) % 12
    if delta > 6:
        delta -= 12

    audio = np.asarray(audio_pitch_classes, dtype=float)
    ranked = np.sort(audio)[::-1]
    top = float(ranked[0]) if ranked.size else 0.0
    second = float(ranked[1]) if ranked.size > 1 else 0.0
    confidence = 0.0 if top <= 0 else max(0.0, min(1.0, (top - second) / top))

    if delta == 0:
        action = "match"
    elif confidence >= auto_threshold:
        action = "safe-transpose-proposal"
    else:
        action = "review"

    return PitchComparison(
        midi_pitch_class=midi_pc,
        midi_pitch_name=PITCH_NAMES[midi_pc],
        audio_pitch_class=audio_pc,
        audio_pitch_name=PITCH_NAMES[audio_pc],
        semitone_delta=delta,
        confidence=round(confidence, 4),
        action=action,
    )


def to_dict(result: PitchComparison | None) -> dict | None:
    return asdict(result) if result else None
