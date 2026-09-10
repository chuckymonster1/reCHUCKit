from io import BytesIO

import mido
from fastapi.testclient import TestClient

import server


def _midi_bytes() -> bytes:
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("note_on", note=40, velocity=100, time=13))
    track.append(mido.Message("note_off", note=40, velocity=0, time=240))
    data = BytesIO()
    mid.save(file=data)
    return data.getvalue()


def test_health():
    client = TestClient(server.app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_midi_upload_builds_downloadable_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "EXPORT_ROOT", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        "/api/rebuild",
        files=[("midi", ("bass.mid", _midi_bytes(), "audio/midi"))],
        data={"humanize": "0.28", "timing": "0.72", "velocity": "0.55"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["report"]["safety"]["source_files_modified"] is False
    assert payload["report"]["analysis"]["midi"][0]["role"]["role"] == "bass"

    download = client.get(payload["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    assert len(download.content) > 0
