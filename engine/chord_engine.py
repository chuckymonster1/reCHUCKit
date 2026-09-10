"""Chord-window comparison for reCHUCKit.

Compares MIDI pitch-class content against audio chroma over time windows.
This module only proposes corrections; it never mutates source MIDI.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter
import mido
import numpy as np

PITCH_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

@dataclass(frozen=True)
class ChordWindow:
    start: float
    end: float
    midi_pitch_classes: list[int]
    audio_pitch_classes: list[int]
    overlap_score: float
    confidence: float
    action: str


def midi_note_events(path: str | Path) -> list[tuple[float, int]]:
    mid = mido.MidiFile(path)
    tempo = mido.bpm2tempo(120)
    absolute = 0.0
    out: list[tuple[float, int]] = []
    for msg in mido.merge_tracks(mid.tracks):
        absolute += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
        if msg.type == "set_tempo":
            tempo = msg.tempo
        elif msg.type == "note_on" and msg.velocity > 0:
            out.append((absolute, msg.note % 12))
    return out


def _top_pitch_classes(values: np.ndarray, top_n: int = 4) -> list[int]:
    if values.size != 12 or np.max(values) <= 0:
        return []
    idx = np.argsort(values)[::-1][:top_n]
    return [int(i) for i in idx if values[i] > 0]


def compare_chord_windows(
    midi_events: list[tuple[float, int]],
    chroma_frames: np.ndarray,
    frame_times: np.ndarray,
    window_seconds: float = 0.5,
    top_n: int = 4,
    auto_threshold: float = 0.88,
) -> list[ChordWindow]:
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    if chroma_frames.ndim != 2 or chroma_frames.shape[0] != 12:
        raise ValueError("chroma_frames must have shape (12, n_frames)")
    if chroma_frames.shape[1] != len(frame_times):
        raise ValueError("frame_times length must match chroma frame count")
    if len(frame_times) == 0:
        return []

    duration = float(frame_times[-1])
    start = 0.0
    results: list[ChordWindow] = []
    while start <= duration:
        end = start + window_seconds
        midi_counts = Counter(pc for t, pc in midi_events if start <= t < end)
        midi_pcs = [pc for pc, _ in midi_counts.most_common(top_n)]

        mask = (frame_times >= start) & (frame_times < end)
        if np.any(mask):
            audio_mean = chroma_frames[:, mask].mean(axis=1)
            audio_pcs = _top_pitch_classes(audio_mean, top_n=top_n)
            ranked = np.sort(audio_mean)[::-1]
            top = float(ranked[0]) if ranked.size else 0.0
            second = float(ranked[1]) if ranked.size > 1 else 0.0
            confidence = 0.0 if top <= 0 else max(0.0, min(1.0, (top-second)/top))
        else:
            audio_pcs = []
            confidence = 0.0

        union = set(midi_pcs) | set(audio_pcs)
        overlap = 1.0 if not union else len(set(midi_pcs) & set(audio_pcs)) / len(union)

        if overlap >= 0.75:
            action = "match"
        elif confidence >= auto_threshold and midi_pcs and audio_pcs:
            action = "safe-correction-proposal"
        else:
            action = "review"

        results.append(ChordWindow(
            start=round(start, 4), end=round(end, 4),
            midi_pitch_classes=midi_pcs,
            audio_pitch_classes=audio_pcs,
            overlap_score=round(float(overlap), 4),
            confidence=round(float(confidence), 4),
            action=action,
        ))
        start = end
    return results


def to_dict(items: list[ChordWindow]) -> list[dict]:
    return [asdict(item) for item in items]
