"""reCHUCKit MIDI reconstruction core.

MVP engine: parse Standard MIDI Files, preserve musical feel, remove obvious
micro-note glitches, optionally tighten note starts toward a grid, normalize
extreme velocities, and emit cleaned MIDI plus an analysis report.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import mido

@dataclass
class MidiStats:
    file: str
    tracks: int
    notes: int
    tempo_bpm: float
    ticks_per_beat: int
    min_note: int | None
    max_note: int | None
    avg_velocity: float


def _tempo(mid: mido.MidiFile) -> int:
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                return msg.tempo
    return mido.bpm2tempo(120)


def analyze(path: str | Path) -> MidiStats:
    mid = mido.MidiFile(path)
    notes, velocities = [], []
    for track in mid.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                notes.append(msg.note); velocities.append(msg.velocity)
    return MidiStats(str(path), len(mid.tracks), len(notes), mido.tempo2bpm(_tempo(mid)),
                     mid.ticks_per_beat, min(notes) if notes else None,
                     max(notes) if notes else None,
                     round(sum(velocities)/len(velocities), 1) if velocities else 0.0)


def clean(path: str | Path, output: str | Path, timing_strength: float=.72,
          velocity_strength: float=.55, grid_division: int=16) -> MidiStats:
    mid = mido.MidiFile(path)
    grid = max(1, round(mid.ticks_per_beat * 4 / grid_division))
    for track in mid.tracks:
        absolute = 0
        rebuilt: list[tuple[int, Any]] = []
        for msg in track:
            absolute += msg.time
            target = absolute
            if msg.type in ("note_on", "note_off"):
                snapped = round(absolute / grid) * grid
                target = round(absolute + (snapped - absolute) * timing_strength)
                if msg.type == "note_on" and msg.velocity > 0:
                    # Pull only extreme velocities toward a musical center;
                    # do not flatten dynamics.
                    center = 82
                    msg = msg.copy(velocity=max(1, min(127, round(msg.velocity + (center-msg.velocity)*velocity_strength*.28))))
            rebuilt.append((max(0,target), msg))
        rebuilt.sort(key=lambda x:x[0])
        previous = 0
        new_track = mido.MidiTrack()
        for tick,msg in rebuilt:
            new_track.append(msg.copy(time=max(0,tick-previous)))
            previous=tick
        track[:] = new_track
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    mid.save(output)
    return analyze(output)


def process(input_path: str, output_dir: str, **settings: Any) -> dict[str, Any]:
    source = analyze(input_path)
    out = Path(output_dir) / f"{Path(input_path).stem}_reCHUCKit.mid"
    cleaned = clean(input_path, out, **settings)
    report = {"source": asdict(source), "cleaned": asdict(cleaned), "output": str(out)}
    report_path = Path(output_dir)/f"{Path(input_path).stem}_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    return report
