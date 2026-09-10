"""Non-destructive MIDI cleanup core for reCHUCKit.

The cleaner tightens note starts without independently quantizing note-offs,
therefore preserving played durations. It also repairs ultra-short notes and
only softens velocity outliers instead of flattening dynamics.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any
import json

import mido


@dataclass(frozen=True)
class MidiStats:
    file: str
    tracks: int
    notes: int
    tempo_bpm: float
    ticks_per_beat: int
    min_note: int | None
    max_note: int | None
    avg_velocity: float


@dataclass(frozen=True)
class CleanupStats:
    shifted_notes: int
    repaired_short_notes: int
    velocity_outliers_adjusted: int
    unmatched_note_ons: int
    unmatched_note_offs: int


def _tempo(mid: mido.MidiFile) -> int:
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                return msg.tempo
    return mido.bpm2tempo(120)


def analyze(path: str | Path) -> MidiStats:
    mid = mido.MidiFile(path)
    notes: list[int] = []
    velocities: list[int] = []
    for track in mid.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                notes.append(msg.note)
                velocities.append(msg.velocity)
    return MidiStats(
        file=str(path),
        tracks=len(mid.tracks),
        notes=len(notes),
        tempo_bpm=round(float(mido.tempo2bpm(_tempo(mid))), 3),
        ticks_per_beat=mid.ticks_per_beat,
        min_note=min(notes) if notes else None,
        max_note=max(notes) if notes else None,
        avg_velocity=round(sum(velocities) / len(velocities), 1) if velocities else 0.0,
    )


def _absolute_events(track: mido.MidiTrack) -> list[dict[str, Any]]:
    tick = 0
    events: list[dict[str, Any]] = []
    for order, msg in enumerate(track):
        tick += msg.time
        events.append({"tick": tick, "order": order, "msg": msg})
    return events


def _is_note_off(msg: mido.Message | mido.MetaMessage) -> bool:
    return msg.type == "note_off" or (msg.type == "note_on" and getattr(msg, "velocity", 0) == 0)


def _cleanup_track(
    track: mido.MidiTrack,
    grid: int,
    timing_strength: float,
    velocity_strength: float,
    humanize_strength: float,
    min_note_ticks: int,
) -> tuple[mido.MidiTrack, CleanupStats]:
    events = _absolute_events(track)
    note_on_indices = [
        i for i, event in enumerate(events)
        if event["msg"].type == "note_on" and event["msg"].velocity > 0
    ]
    velocities = [events[i]["msg"].velocity for i in note_on_indices]
    velocity_center = float(median(velocities)) if len(velocities) >= 3 else 82.0

    active: dict[tuple[int, int], deque[int]] = defaultdict(deque)
    pairs: list[tuple[int, int]] = []
    unmatched_offs = 0
    for index, event in enumerate(events):
        msg = event["msg"]
        if not hasattr(msg, "channel") or not hasattr(msg, "note"):
            continue
        key = (msg.channel, msg.note)
        if msg.type == "note_on" and msg.velocity > 0:
            active[key].append(index)
        elif _is_note_off(msg):
            if active[key]:
                pairs.append((active[key].popleft(), index))
            else:
                unmatched_offs += 1
    unmatched_ons = sum(len(queue) for queue in active.values())

    shifted = 0
    repaired = 0
    velocity_adjusted = 0
    # Humanize is implemented as groove preservation, not random jitter.
    effective_timing = timing_strength * (1.0 - 0.60 * humanize_strength)

    for on_index, off_index in pairs:
        on_event = events[on_index]
        off_event = events[off_index]
        original_on = int(on_event["tick"])
        original_off = int(off_event["tick"])
        duration = max(0, original_off - original_on)
        snapped = round(original_on / grid) * grid
        new_on = max(0, round(original_on + (snapped - original_on) * effective_timing))
        delta = new_on - original_on
        if delta:
            shifted += 1
        new_off = max(new_on + min_note_ticks, original_off + delta)
        if duration < min_note_ticks:
            repaired += 1
        on_event["tick"] = new_on
        off_event["tick"] = new_off

    for index in note_on_indices:
        msg = events[index]["msg"]
        velocity = msg.velocity
        # Only touch clear outliers; leave normal expressive dynamics alone.
        if velocity < 24 or velocity > 116:
            new_velocity = round(velocity + (velocity_center - velocity) * velocity_strength)
            new_velocity = max(1, min(127, new_velocity))
            if new_velocity != velocity:
                events[index]["msg"] = msg.copy(velocity=new_velocity)
                velocity_adjusted += 1

    # Stable ordering: original order breaks ties at the same absolute tick.
    events.sort(key=lambda item: (int(item["tick"]), int(item["order"])))
    rebuilt = mido.MidiTrack()
    previous_tick = 0
    for event in events:
        tick = int(event["tick"])
        rebuilt.append(event["msg"].copy(time=max(0, tick - previous_tick)))
        previous_tick = tick

    return rebuilt, CleanupStats(
        shifted_notes=shifted,
        repaired_short_notes=repaired,
        velocity_outliers_adjusted=velocity_adjusted,
        unmatched_note_ons=unmatched_ons,
        unmatched_note_offs=unmatched_offs,
    )


def clean(
    path: str | Path,
    output: str | Path,
    timing_strength: float = 0.72,
    velocity_strength: float = 0.55,
    humanize_strength: float = 0.28,
    grid_division: int = 16,
    min_note_fraction: int = 64,
) -> tuple[MidiStats, CleanupStats]:
    for value, label in (
        (timing_strength, "timing_strength"),
        (velocity_strength, "velocity_strength"),
        (humanize_strength, "humanize_strength"),
    ):
        if not 0 <= value <= 1:
            raise ValueError(f"{label} must be between 0 and 1")
    if grid_division <= 0 or min_note_fraction <= 0:
        raise ValueError("grid_division and min_note_fraction must be positive")

    source = Path(path)
    destination = Path(output)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == destination.resolve():
        raise ValueError("Refusing to overwrite source MIDI")

    mid = mido.MidiFile(source)
    grid = max(1, round(mid.ticks_per_beat * 4 / grid_division))
    min_note_ticks = max(1, round(mid.ticks_per_beat * 4 / min_note_fraction))

    aggregate = CleanupStats(0, 0, 0, 0, 0)
    for track_index, track in enumerate(mid.tracks):
        rebuilt, stats = _cleanup_track(
            track,
            grid,
            timing_strength,
            velocity_strength,
            humanize_strength,
            min_note_ticks,
        )
        mid.tracks[track_index] = rebuilt
        aggregate = CleanupStats(
            shifted_notes=aggregate.shifted_notes + stats.shifted_notes,
            repaired_short_notes=aggregate.repaired_short_notes + stats.repaired_short_notes,
            velocity_outliers_adjusted=aggregate.velocity_outliers_adjusted + stats.velocity_outliers_adjusted,
            unmatched_note_ons=aggregate.unmatched_note_ons + stats.unmatched_note_ons,
            unmatched_note_offs=aggregate.unmatched_note_offs + stats.unmatched_note_offs,
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    mid.save(destination)
    return analyze(destination), aggregate


def process(input_path: str, output_dir: str, **settings: Any) -> dict[str, Any]:
    source = analyze(input_path)
    out = Path(output_dir) / f"{Path(input_path).stem}_reCHUCKit.mid"
    cleaned, cleanup = clean(input_path, out, **settings)
    report = {
        "source": asdict(source),
        "cleaned": asdict(cleaned),
        "cleanup": asdict(cleanup),
        "output": str(out),
    }
    report_path = Path(output_dir) / f"{Path(input_path).stem}_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
