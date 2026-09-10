"""Apply vetted reCHUCKit MIDI corrections non-destructively.

The correction engine takes explicit, confidence-approved edit instructions and
writes a NEW MIDI file. Source files are never overwritten.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import json
import mido


@dataclass(frozen=True)
class NoteCorrection:
    track_index: int
    note_index: int
    original_note: int
    replacement_note: int
    confidence: float
    reason: str


@dataclass(frozen=True)
class CorrectionResult:
    source: str
    output: str
    applied: int
    skipped: int
    corrections: list[dict]


def _validate_note(note: int) -> None:
    if not 0 <= note <= 127:
        raise ValueError(f"MIDI note must be 0..127, got {note}")


def apply_note_corrections(
    source_path: str | Path,
    output_path: str | Path,
    corrections: Iterable[NoteCorrection],
    min_confidence: float = 0.92,
) -> CorrectionResult:
    source = Path(source_path)
    output = Path(output_path)
    if source.resolve() == output.resolve():
        raise ValueError("Output path must differ from source path")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be between 0 and 1")

    mid = mido.MidiFile(source)
    requested = list(corrections)
    for corr in requested:
        _validate_note(corr.original_note)
        _validate_note(corr.replacement_note)
        if not 0.0 <= corr.confidence <= 1.0:
            raise ValueError("Correction confidence must be between 0 and 1")
        if corr.track_index < 0 or corr.track_index >= len(mid.tracks):
            raise IndexError(f"Invalid track_index: {corr.track_index}")

    by_target = {(c.track_index, c.note_index): c for c in requested}
    note_counters = [0] * len(mid.tracks)
    applied = 0
    skipped = 0
    audit: list[dict] = []

    for track_idx, track in enumerate(mid.tracks):
        active_replacements: dict[tuple[int, int], int] = {}
        for msg_idx, msg in enumerate(track):
            if msg.type == "note_on" and msg.velocity > 0:
                note_idx = note_counters[track_idx]
                note_counters[track_idx] += 1
                corr = by_target.get((track_idx, note_idx))
                if corr is None:
                    continue
                if corr.confidence < min_confidence or msg.note != corr.original_note:
                    skipped += 1
                    audit.append({**asdict(corr), "status": "skipped"})
                    continue
                old_note = msg.note
                track[msg_idx] = msg.copy(note=corr.replacement_note)
                active_replacements[(msg.channel, old_note)] = corr.replacement_note
                applied += 1
                audit.append({**asdict(corr), "status": "applied"})

            elif msg.type in ("note_off", "note_on") and getattr(msg, "velocity", 0) == 0:
                key = (getattr(msg, "channel", 0), msg.note)
                if key in active_replacements:
                    track[msg_idx] = msg.copy(note=active_replacements.pop(key))

    output.parent.mkdir(parents=True, exist_ok=True)
    mid.save(output)
    return CorrectionResult(
        source=str(source),
        output=str(output),
        applied=applied,
        skipped=skipped,
        corrections=audit,
    )


def write_audit_log(result: CorrectionResult, path: str | Path) -> None:
    Path(path).write_text(json.dumps(asdict(result), indent=2))
