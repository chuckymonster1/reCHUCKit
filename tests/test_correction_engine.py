from pathlib import Path

import mido
import pytest

from engine.correction_engine import NoteCorrection, apply_note_corrections


def _make_midi(path: Path):
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("note_on", note=60, velocity=90, time=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=480))
    mid.save(path)


def test_high_confidence_note_is_changed_and_note_off_matches(tmp_path):
    src = tmp_path / "src.mid"
    out = tmp_path / "out.mid"
    _make_midi(src)
    result = apply_note_corrections(
        src,
        out,
        [NoteCorrection(0, 0, 60, 62, 0.99, "audio match")],
    )
    assert result.applied == 1
    mid = mido.MidiFile(out)
    notes = [m.note for m in mid.tracks[0] if m.type in ("note_on", "note_off")]
    assert notes == [62, 62]


def test_low_confidence_note_is_not_changed(tmp_path):
    src = tmp_path / "src.mid"
    out = tmp_path / "out.mid"
    _make_midi(src)
    result = apply_note_corrections(
        src,
        out,
        [NoteCorrection(0, 0, 60, 62, 0.50, "weak evidence")],
    )
    assert result.applied == 0 and result.skipped == 1
    mid = mido.MidiFile(out)
    first_note = next(m.note for m in mid.tracks[0] if m.type == "note_on")
    assert first_note == 60


def test_source_overwrite_is_refused(tmp_path):
    src = tmp_path / "src.mid"
    _make_midi(src)
    with pytest.raises(ValueError):
        apply_note_corrections(src, src, [])
