from pathlib import Path
import json
import zipfile
import pytest
from engine.exporter import export_session


def test_export_session_builds_portable_zip(tmp_path: Path):
    midi = tmp_path / "keys.mid"
    stem = tmp_path / "keys.wav"
    ref = tmp_path / "reference.wav"
    midi.write_bytes(b"MThd")
    stem.write_bytes(b"RIFF")
    ref.write_bytes(b"RIFF")

    out = tmp_path / "out"
    zip_path = export_session(
        "Test Song",
        out,
        corrected_midi=[midi],
        stems=[stem],
        reference=ref,
        report={"tempo": 120},
    )

    assert zip_path.exists()
    root = out / "Test Song_reCHUCKit_EXPORT"
    assert (root / "MIDI" / "keys.mid").exists()
    assert (root / "WAV_STEMS" / "keys.wav").exists()
    assert (root / "REFERENCE" / "reference.wav").exists()
    payload = json.loads((root / "session.json").read_text())
    assert payload["report"]["tempo"] == 120

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "Test Song_reCHUCKit_EXPORT/MIDI/keys.mid" in names
        assert "Test Song_reCHUCKit_EXPORT/WAV_STEMS/keys.wav" in names


def test_export_refuses_overwrite(tmp_path: Path):
    midi = tmp_path / "keys.mid"
    midi.write_bytes(b"MThd")
    out = tmp_path / "out"
    export_session("Song", out, corrected_midi=[midi])
    with pytest.raises(FileExistsError):
        export_session("Song", out, corrected_midi=[midi])


def test_export_rejects_missing_source(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        export_session("Song", tmp_path / "out", corrected_midi=[tmp_path / "missing.mid"])
