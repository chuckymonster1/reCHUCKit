from pathlib import Path

import mido
import pytest

from engine.midi_engine import clean


def _write_midi(path: Path, note_on_tick: int = 17, duration: int = 120, velocity: int = 100) -> None:
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("note_on", note=60, velocity=velocity, time=note_on_tick))
    track.append(mido.Message("note_off", note=60, velocity=0, time=duration))
    mid.save(path)


def _note_ticks(path: Path) -> tuple[int, int, int]:
    mid = mido.MidiFile(path)
    absolute = 0
    start = end = velocity = None
    for msg in mid.tracks[0]:
        absolute += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            start, velocity = absolute, msg.velocity
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            end = absolute
    assert start is not None and end is not None and velocity is not None
    return start, end, velocity


def test_cleanup_preserves_note_duration(tmp_path):
    source = tmp_path / "source.mid"
    output = tmp_path / "clean.mid"
    _write_midi(source, note_on_tick=17, duration=120)

    clean(source, output, timing_strength=1.0, humanize_strength=0.0)
    start, end, _ = _note_ticks(output)

    assert end - start == 120


def test_cleanup_repairs_micro_note(tmp_path):
    source = tmp_path / "source.mid"
    output = tmp_path / "clean.mid"
    _write_midi(source, note_on_tick=0, duration=1)

    _, stats = clean(source, output, timing_strength=0.0, min_note_fraction=64)
    start, end, _ = _note_ticks(output)

    assert end > start
    assert stats.repaired_short_notes == 1


def test_velocity_cleanup_only_moves_extreme_outlier(tmp_path):
    source = tmp_path / "source.mid"
    output = tmp_path / "clean.mid"
    _write_midi(source, velocity=127)

    clean(source, output, timing_strength=0.0, velocity_strength=1.0)
    _, _, velocity = _note_ticks(output)

    assert 1 <= velocity < 127


def test_source_overwrite_is_refused(tmp_path):
    source = tmp_path / "source.mid"
    _write_midi(source)

    with pytest.raises(ValueError, match="overwrite source"):
        clean(source, source)
