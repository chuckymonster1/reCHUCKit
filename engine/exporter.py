"""DAW-ready session package exporter for reCHUCKit.

Creates a portable ZIP containing corrected MIDI, reference audio, stems,
and a machine-readable session report. Sources are copied; never modified.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import copy2
from typing import Iterable
import json
import zipfile


@dataclass(frozen=True)
class ExportManifest:
    session_name: str
    reference: str | None
    midi_files: list[str]
    stems: list[str]
    daw_targets: list[str]


def _safe_name(name: str) -> str:
    keep = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    cleaned = "".join(c for c in name if c in keep).strip()
    return cleaned or "untitled"


def _copy_many(paths: Iterable[str | Path], destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for item in paths:
        src = Path(item)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(src)
        target = destination / _safe_name(src.name)
        if target.exists():
            raise FileExistsError(f"Duplicate export filename: {target.name}")
        copy2(src, target)
        copied.append(target.name)
    return copied


def export_session(
    session_name: str,
    output_dir: str | Path,
    corrected_midi: Iterable[str | Path],
    stems: Iterable[str | Path] = (),
    reference: str | Path | None = None,
    report: dict | None = None,
    daw_targets: Iterable[str] = ("Logic Pro", "Reason"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_session = _safe_name(session_name)
    root = output_dir / f"{safe_session}_reCHUCKit_EXPORT"
    if root.exists():
        raise FileExistsError(f"Refusing to overwrite existing export: {root}")

    midi_dir = root / "MIDI"
    stems_dir = root / "WAV_STEMS"
    ref_dir = root / "REFERENCE"
    docs_dir = root / "DOCS"
    docs_dir.mkdir(parents=True, exist_ok=True)

    midi_names = _copy_many(corrected_midi, midi_dir)
    stem_names = _copy_many(stems, stems_dir)

    reference_name: str | None = None
    if reference is not None:
        ref = Path(reference)
        if not ref.exists() or not ref.is_file():
            raise FileNotFoundError(ref)
        ref_dir.mkdir(parents=True, exist_ok=True)
        target = ref_dir / _safe_name(ref.name)
        copy2(ref, target)
        reference_name = target.name

    targets = list(daw_targets)
    manifest = ExportManifest(
        session_name=session_name,
        reference=reference_name,
        midi_files=midi_names,
        stems=stem_names,
        daw_targets=targets,
    )
    payload = {"manifest": asdict(manifest), "report": report or {}}
    (root / "session.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    guide = (
        "reCHUCKit DAW IMPORT GUIDE\n\n"
        "1. Set your DAW session tempo/key from session.json or the analysis report.\n"
        "2. Import all WAV stems at timeline 00:00.\n"
        "3. Import MIDI by role and assign instruments/plugins manually.\n"
        "4. Keep the REFERENCE track muted for A/B comparison.\n"
        "5. This package does not generate native .logicx or Reason project files.\n"
        "6. MIDI does not contain instrument tone; patch/plugin matching is a separate step.\n"
    )
    (docs_dir / "IMPORT_GUIDE.txt").write_text(guide, encoding="utf-8")

    zip_path = output_dir / f"{safe_session}_reCHUCKit.zip"
    if zip_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing archive: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in root.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(root.parent))
    return zip_path
