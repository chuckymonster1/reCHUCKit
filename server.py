"""reCHUCKit web/API entry point.

Serves the browser UI and runs the first usable end-to-end V1 pipeline:
upload -> audio analysis -> non-destructive MIDI cleanup -> DAW export ZIP.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated
from uuid import uuid4
import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from engine.audio_analyzer import analyze_audio
from engine.exporter import export_session
from engine.midi_engine import process as process_midi

ROOT = Path(__file__).resolve().parent
EXPORT_ROOT = ROOT / "exports"
MAX_FILE_BYTES = 250 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
ALLOWED_AUDIO = {".wav", ".mp3", ".m4a", ".aif", ".aiff", ".flac", ".ogg"}
ALLOWED_MIDI = {".mid", ".midi"}

app = FastAPI(title="reCHUCKit", version="0.1.0")


def _safe_name(name: str) -> str:
    name = Path(name or "upload").name
    keep = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    clean = "".join(ch for ch in name if ch in keep).strip(" .")
    return clean or "upload"


async def _save_upload(upload: UploadFile, destination: Path, allowed: set[str]) -> Path:
    filename = _safe_name(upload.filename or "upload")
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(415, f"Unsupported file type: {suffix or 'none'}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with destination.open("wb") as handle:
            while chunk := await upload.read(CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(
                        413,
                        f"File is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB",
                    )
                handle.write(chunk)
    finally:
        await upload.close()
    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, f"Empty upload: {filename}")
    return destination


def _public_midi_report(report: dict) -> dict:
    clean = json.loads(json.dumps(report))
    for section in ("source", "cleaned"):
        if section in clean and "file" in clean[section]:
            clean[section]["file"] = Path(clean[section]["file"]).name
    if "output" in clean:
        clean["output"] = Path(clean["output"]).name
    return clean


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/styles.css")
def styles() -> FileResponse:
    return FileResponse(ROOT / "styles.css", media_type="text/css")


@app.get("/app.js")
def javascript() -> FileResponse:
    return FileResponse(ROOT / "app.js", media_type="application/javascript")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "engine": "reCHUCKit", "version": app.version}


@app.post("/api/rebuild")
async def rebuild(
    reference: Annotated[UploadFile | None, File()] = None,
    stems: Annotated[list[UploadFile] | None, File()] = None,
    midi: Annotated[list[UploadFile] | None, File()] = None,
    humanize: Annotated[float, Form()] = 0.28,
    timing: Annotated[float, Form()] = 0.72,
    velocity: Annotated[float, Form()] = 0.55,
) -> dict:
    stems = stems or []
    midi = midi or []
    if reference is None and not stems and not midi:
        raise HTTPException(400, "Upload a reference mix, stems, or MIDI first.")
    for value, label in (
        (humanize, "humanize"),
        (timing, "timing"),
        (velocity, "velocity"),
    ):
        if not 0 <= value <= 1:
            raise HTTPException(422, f"{label} must be between 0 and 1")

    job_id = uuid4().hex
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    first_name = reference.filename if reference else (midi[0].filename if midi else stems[0].filename)
    session_name = Path(first_name or "session").stem

    with TemporaryDirectory(prefix="rechuckit-") as temp:
        work = Path(temp)
        upload_dir = work / "uploads"
        processed_dir = work / "processed"
        upload_dir.mkdir(parents=True)
        processed_dir.mkdir(parents=True)

        reference_path: Path | None = None
        if reference is not None:
            reference_path = await _save_upload(
                reference,
                upload_dir / f"reference_{_safe_name(reference.filename or 'mix.wav')}",
                ALLOWED_AUDIO,
            )

        stem_paths: list[Path] = []
        for index, item in enumerate(stems, 1):
            stem_paths.append(
                await _save_upload(
                    item,
                    upload_dir / f"stem_{index:02d}_{_safe_name(item.filename or 'stem.wav')}",
                    ALLOWED_AUDIO,
                )
            )

        midi_paths: list[Path] = []
        for index, item in enumerate(midi, 1):
            midi_paths.append(
                await _save_upload(
                    item,
                    upload_dir / f"midi_{index:02d}_{_safe_name(item.filename or 'track.mid')}",
                    ALLOWED_MIDI,
                )
            )

        analysis: dict = {"reference": None, "stems": [], "midi": []}
        if reference_path:
            analysis["reference"] = asdict(analyze_audio(reference_path))
            analysis["reference"]["file"] = Path(analysis["reference"]["file"]).name
        for path in stem_paths:
            features = asdict(analyze_audio(path))
            features["file"] = Path(features["file"]).name
            analysis["stems"].append(features)

        corrected_midi: list[Path] = []
        for path in midi_paths:
            result = process_midi(
                str(path),
                str(processed_dir),
                timing_strength=timing,
                velocity_strength=velocity,
                humanize_strength=humanize,
            )
            corrected_midi.append(Path(result["output"]))
            analysis["midi"].append(_public_midi_report(result))

        report = {
            "job_id": job_id,
            "session": session_name,
            "settings": {"humanize": humanize, "timing": timing, "velocity": velocity},
            "analysis": analysis,
            "safety": {
                "source_files_modified": False,
                "automatic_pitch_corrections_applied": False,
                "note": (
                    "V1 applies timing/velocity cleanup only. Pitch/note proposals remain "
                    "review-gated until confidence validation is wired into the pipeline."
                ),
            },
        }

        job_dir = EXPORT_ROOT / job_id
        job_dir.mkdir()
        export_session(
            session_name=session_name,
            output_dir=job_dir,
            corrected_midi=corrected_midi,
            stems=stem_paths,
            reference=reference_path,
            report=report,
        )

    return {
        "job_id": job_id,
        "session": session_name,
        "download_url": f"/api/download/{job_id}",
        "report": report,
        "message": "Reconstruction package ready.",
    }


@app.get("/api/download/{job_id}")
def download(job_id: str) -> FileResponse:
    if not job_id.isalnum() or len(job_id) != 32:
        raise HTTPException(404, "Export not found")
    job_dir = EXPORT_ROOT / job_id
    archives = list(job_dir.glob("*_reCHUCKit.zip")) if job_dir.exists() else []
    if len(archives) != 1:
        raise HTTPException(404, "Export not found")
    return FileResponse(archives[0], media_type="application/zip", filename=archives[0].name)
