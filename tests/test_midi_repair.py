from pathlib import Path
import mido
import pytest
from engine.midi_repair import repair_midi_metadata


def _bad_key_signature_midi(path: Path):
    # Minimal SMF with invalid +13 sharps metadata followed by a valid note.
    track = bytes.fromhex("00ff59020d0100903c64008360803c0000ff2f00")
    header = bytes.fromhex("4d546864000000060000000101e0")
    chunk = b"MTrk" + len(track).to_bytes(4, "big") + track
    path.write_bytes(header + chunk)


def test_repairs_invalid_key_signature_without_touching_notes(tmp_path):
    src = tmp_path / "suno.mid"; out = tmp_path / "repaired.mid"
    _bad_key_signature_midi(src)
    repairs = repair_midi_metadata(src, out)
    assert len(repairs) == 1
    assert repairs[0].original == 13 and repairs[0].replacement == 7
    mid = mido.MidiFile(out)
    notes = [m.note for t in mid.tracks for m in t if m.type == "note_on" and m.velocity > 0]
    assert notes == [60]


def test_source_is_never_overwritten(tmp_path):
    src = tmp_path / "suno.mid"; _bad_key_signature_midi(src)
    with pytest.raises(ValueError):
        repair_midi_metadata(src, src)
