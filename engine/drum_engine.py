"""Drum-specific MIDI analysis for reCHUCKit.

General MIDI percussion uses channel 10 (zero-based channel 9). This module
classifies hits into musical families and reports uncertainty. It deliberately
does not auto-remap notes without an audio-backed target.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import mido


@dataclass(frozen=True)
class DrumReport:
    is_drum_track: bool
    confidence: float
    total_hits: int
    families: dict[str, int]
    unmapped_notes: dict[int, int]
    note_histogram: dict[int, int]


FAMILIES = {
    "kick": {35, 36},
    "snare": {38, 40},
    "clap": {39},
    "rim": {37},
    "closed_hat": {42, 44},
    "open_hat": {46},
    "tom": {41, 43, 45, 47, 48, 50},
    "crash": {49, 52, 55, 57},
    "ride": {51, 53, 59},
    "perc": {54, 56, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81},
}
NOTE_TO_FAMILY = {note: family for family, notes in FAMILIES.items() for note in notes}


def analyze_drums(path: str | Path) -> DrumReport:
    mid = mido.MidiFile(Path(path))
    drum_hits: Counter[int] = Counter()
    all_hits = 0
    channel_10_hits = 0

    for track in mid.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                all_hits += 1
                if msg.channel == 9:
                    channel_10_hits += 1
                    drum_hits[msg.note] += 1

    if all_hits == 0:
        return DrumReport(False, 0.0, 0, {}, {}, {})

    fraction = channel_10_hits / all_hits
    is_drum = fraction >= 0.8
    confidence = min(0.99, fraction if is_drum else fraction * 0.6)
    families: Counter[str] = Counter()
    unmapped: dict[int, int] = {}
    for note, count in drum_hits.items():
        family = NOTE_TO_FAMILY.get(note)
        if family:
            families[family] += count
        else:
            unmapped[note] = count

    return DrumReport(
        is_drum_track=is_drum,
        confidence=round(confidence, 3),
        total_hits=channel_10_hits,
        families=dict(sorted(families.items())),
        unmapped_notes=dict(sorted(unmapped.items())),
        note_histogram=dict(sorted(drum_hits.items())),
    )


def to_dict(report: DrumReport) -> dict:
    return asdict(report)
