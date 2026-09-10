"""Confidence-scored MIDI role detection for reCHUCKit.

Role detection never pretends MIDI contains instrument tone. It combines filename
hints with measurable MIDI behavior and returns reasons/confidence for review.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import mido


@dataclass(frozen=True)
class RoleResult:
    role: str
    confidence: float
    reasons: list[str]
    note_count: int
    median_note: float | None
    drum_channel_fraction: float


ROLE_HINTS = {
    "drums": ("drum", "kick", "snare", "hat", "hihat", "perc", "cymbal", "tom"),
    "bass": ("bass", "sub", "808"),
    "guitar": ("guitar", "gtr", "acoustic", "electric"),
    "keys": ("piano", "keys", "keyboard", "rhodes", "organ", "ep"),
    "strings": ("string", "violin", "viola", "cello"),
    "vocals": ("vocal", "voice", "lead vox", "vox"),
}


def detect_role(path: str | Path) -> RoleResult:
    source = Path(path)
    mid = mido.MidiFile(source)
    notes: list[int] = []
    drum_notes = 0
    total_notes = 0
    channels: set[int] = set()

    for track in mid.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                total_notes += 1
                notes.append(msg.note)
                channels.add(msg.channel)
                if msg.channel == 9:
                    drum_notes += 1

    if not notes:
        return RoleResult("unknown", 0.0, ["No note-on events found"], 0, None, 0.0)

    notes_sorted = sorted(notes)
    midpoint = len(notes_sorted) // 2
    median_note = (
        float(notes_sorted[midpoint])
        if len(notes_sorted) % 2
        else (notes_sorted[midpoint - 1] + notes_sorted[midpoint]) / 2
    )
    drum_fraction = drum_notes / total_notes
    name = source.stem.lower().replace("_", " ").replace("-", " ")
    reasons: list[str] = []
    scores: dict[str, float] = {key: 0.0 for key in ROLE_HINTS}

    for role, hints in ROLE_HINTS.items():
        if any(hint in name for hint in hints):
            scores[role] += 0.72
            reasons.append(f"Filename suggests {role}")

    if drum_fraction >= 0.8:
        scores["drums"] += 0.95
        reasons.append("Most notes use General MIDI percussion channel 10")
    elif drum_fraction > 0:
        scores["drums"] += 0.45 * drum_fraction
        reasons.append("Some notes use General MIDI percussion channel 10")

    if median_note < 48 and drum_fraction < 0.5:
        scores["bass"] += 0.42
        reasons.append("Pitch register is strongly bass-weighted")
    elif median_note < 55 and drum_fraction < 0.5:
        scores["bass"] += 0.24
        reasons.append("Pitch register leans low")

    # MIDI cannot reliably separate guitar/keys/strings without timbre evidence.
    best_role = max(scores, key=scores.get)
    best_score = scores[best_role]
    if best_score <= 0:
        best_role = "melodic"
        best_score = 0.35
        reasons.append("No reliable role-specific evidence; treating as generic melodic MIDI")

    confidence = min(0.99, best_score)
    return RoleResult(
        role=best_role,
        confidence=round(confidence, 3),
        reasons=reasons,
        note_count=total_notes,
        median_note=round(median_note, 2),
        drum_channel_fraction=round(drum_fraction, 3),
    )


def to_dict(result: RoleResult) -> dict:
    return asdict(result)
