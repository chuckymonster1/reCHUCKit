"""Confidence-scored audio/MIDI timing comparison.

Corrections are proposals, not destructive edits. This gives the UI and future
engine a reviewable audit trail and prevents uncertain analysis from damaging
source MIDI.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import mido
import numpy as np


@dataclass(frozen=True)
class AlignmentProposal:
    midi_time: float
    audio_onset_time: float
    delta_seconds: float
    confidence: float
    action: str


def midi_note_on_times(path: str | Path) -> list[float]:
    mid = mido.MidiFile(path)
    tempo = mido.bpm2tempo(120)
    absolute_seconds = 0.0
    times: list[float] = []
    # merged track preserves chronological ordering and tempo changes
    for msg in mido.merge_tracks(mid.tracks):
        absolute_seconds += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
        if msg.type == "set_tempo":
            tempo = msg.tempo
        elif msg.type == "note_on" and msg.velocity > 0:
            times.append(absolute_seconds)
    return times


def compare_onsets(midi_times: list[float], audio_onsets: list[float],
                   tolerance_seconds: float = 0.08,
                   auto_threshold: float = 0.90) -> list[AlignmentProposal]:
    if tolerance_seconds <= 0:
        raise ValueError("tolerance_seconds must be positive")
    if not audio_onsets:
        return []
    audio = np.asarray(audio_onsets, dtype=float)
    proposals: list[AlignmentProposal] = []
    for mt in midi_times:
        idx = int(np.argmin(np.abs(audio - mt)))
        at = float(audio[idx])
        delta = at - mt
        distance = abs(delta)
        confidence = max(0.0, 1.0 - distance / tolerance_seconds)
        if distance > tolerance_seconds:
            action = "leave"
        elif confidence >= auto_threshold:
            action = "safe-snap"
        else:
            action = "review"
        proposals.append(AlignmentProposal(
            midi_time=round(mt, 6), audio_onset_time=round(at, 6),
            delta_seconds=round(delta, 6), confidence=round(confidence, 4),
            action=action,
        ))
    return proposals


def proposals_to_dict(items: list[AlignmentProposal]) -> list[dict]:
    return [asdict(item) for item in items]
