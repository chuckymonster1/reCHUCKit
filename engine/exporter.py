"""Build a DAW-neutral reCHUCKit export package.

Every audio stem should begin at project zero. Logic Pro and Reason can then
import the WAV and MIDI assets without proprietary project-file generation.
"""
from pathlib import Path
import json, shutil


def build_export(project_name: str, destination: str, midi_files=None, stem_files=None,
                 reference_mix=None, bpm=None, key=None):
    root=Path(destination)/f"{project_name}_reCHUCKit_EXPORT"
    midi_dir=root/'MIDI'; stems_dir=root/'WAV_STEMS'; ref_dir=root/'REFERENCE'
    for d in (midi_dir,stems_dir,ref_dir): d.mkdir(parents=True,exist_ok=True)
    copied={"midi":[],"stems":[]}
    for src in midi_files or []:
        dst=midi_dir/Path(src).name; shutil.copy2(src,dst); copied['midi'].append(str(dst))
    for src in stem_files or []:
        dst=stems_dir/Path(src).name; shutil.copy2(src,dst); copied['stems'].append(str(dst))
    if reference_mix:
        shutil.copy2(reference_mix,ref_dir/Path(reference_mix).name)
    manifest={"project":project_name,"bpm":bpm,"key":key,"import_start":"00:00.000",
              "logic_pro":"Import all MIDI and WAV stems at project start.",
              "reason":"Import all MIDI and WAV stems at project start.",**copied}
    (root/'reCHUCKit_manifest.json').write_text(json.dumps(manifest,indent=2))
    (root/'IMPORT_ME_FIRST.txt').write_text(
        f"reCHUCKit — {project_name}\n\n1. Set DAW tempo to {bpm or 'detected BPM'}.\n"
        "2. Import every WAV stem at 00:00.000.\n3. Import MIDI at 00:00.000.\n"
        "4. Assign instruments/patches to MIDI tracks.\n5. Use REFERENCE as the A/B target.\n")
    return str(root)
