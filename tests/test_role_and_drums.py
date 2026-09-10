from pathlib import Path

import mido

from engine.drum_engine import analyze_drums
from engine.role_engine import detect_role


def _write(path: Path, channel: int, notes: list[int]) -> None:
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    for note in notes:
        track.append(mido.Message("note_on", channel=channel, note=note, velocity=90, time=0))
        track.append(mido.Message("note_off", channel=channel, note=note, velocity=0, time=120))
    mid.save(path)


def test_channel_10_is_detected_as_drums(tmp_path):
    path = tmp_path / "drums.mid"
    _write(path, 9, [36, 38, 42, 46])

    role = detect_role(path)
    drums = analyze_drums(path)

    assert role.role == "drums"
    assert drums.is_drum_track is True
    assert drums.families["kick"] == 1
    assert drums.families["snare"] == 1
    assert drums.families["closed_hat"] == 1
    assert drums.families["open_hat"] == 1


def test_low_register_filename_can_identify_bass(tmp_path):
    path = tmp_path / "main_bass.mid"
    _write(path, 0, [36, 40, 43, 36])

    result = detect_role(path)

    assert result.role == "bass"
    assert result.confidence >= 0.7
