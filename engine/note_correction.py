"""Surgical note-level comparison for reCHUCKit.

Given MIDI note events and audio chroma evidence, identify likely correct,
missing, and extra pitch classes inside short musical windows. This module
produces reviewable proposals only; source MIDI remains untouched.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import Counter
import numpy as np

@dataclass(frozen=True)
class NoteProposal:
    start: float
    end: float
    matched_pitch_classes: list[int]
    missing_pitch_classes: list[int]
    extra_pitch_classes: list[int]
    confidence: float
    action: str


def _audio_candidates(chroma_window: np.ndarray, threshold_ratio: float = 0.55) -> tuple[list[int], float]:
    if chroma_window.ndim != 2 or chroma_window.shape[0] != 12:
        raise ValueError("chroma_window must have shape (12, n_frames)")
    if chroma_window.shape[1] == 0:
        return [], 0.0
    mean = chroma_window.mean(axis=1)
    top = float(mean.max())
    if top <= 0:
        return [], 0.0
    pcs = [int(i) for i, v in enumerate(mean) if float(v) >= top * threshold_ratio]
    ranked = np.sort(mean)[::-1]
    second = float(ranked[1]) if ranked.size > 1 else 0.0
    confidence = max(0.0, min(1.0, (top - second) / top))
    return pcs, confidence


def compare_note_content(
    midi_events: list[tuple[float, int]],
    chroma_frames: np.ndarray,
    frame_times: np.ndarray,
    window_seconds: float = 0.25,
    audio_threshold_ratio: float = 0.55,
    auto_threshold: float = 0.92,
) -> list[NoteProposal]:
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    if chroma_frames.ndim != 2 or chroma_frames.shape[0] != 12:
        raise ValueError("chroma_frames must have shape (12, n_frames)")
    if chroma_frames.shape[1] != len(frame_times):
        raise ValueError("frame_times length must match chroma frame count")
    if len(frame_times) == 0:
        return []

    results: list[NoteProposal] = []
    start = 0.0
    duration = float(frame_times[-1])
    while start <= duration:
        end = start + window_seconds
        midi_counts = Counter(pc for t, pc in midi_events if start <= t < end)
        midi_pcs = sorted(midi_counts.keys())
        mask = (frame_times >= start) & (frame_times < end)
        audio_pcs, confidence = _audio_candidates(
            chroma_frames[:, mask], threshold_ratio=audio_threshold_ratio
        ) if np.any(mask) else ([], 0.0)

        midi_set, audio_set = set(midi_pcs), set(audio_pcs)
        matched = sorted(midi_set & audio_set)
        missing = sorted(audio_set - midi_set)
        extra = sorted(midi_set - audio_set)

        if not missing and not extra:
            action = "match"
        elif confidence >= auto_threshold and (missing or extra):
            action = "safe-note-proposal"
        else:
            action = "review"

        results.append(NoteProposal(
            start=round(start, 4),
            end=round(end, 4),
            matched_pitch_classes=matched,
            missing_pitch_classes=missing,
            extra_pitch_classes=extra,
            confidence=round(float(confidence), 4),
            action=action,
        ))
        start = end
    return results


def to_dict(items: list[NoteProposal]) -> list[dict]:
    return [asdict(item) for item in items]
