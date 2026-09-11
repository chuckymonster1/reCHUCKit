"""Defensive repair for malformed Standard MIDI metadata.

Some generators emit key-signature meta events whose signed sharps/flats byte is
outside the SMF-defined -7..7 range. mido correctly rejects those files before
reCHUCKit can inspect their notes. This module repairs only that invalid metadata
byte in a copied file; note, timing, velocity, controller, and SysEx bytes remain
untouched.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import struct


@dataclass(frozen=True)
class MidiRepair:
    offset: int
    field: str
    original: int
    replacement: int


def repair_midi_metadata(source: str | Path, destination: str | Path) -> list[MidiRepair]:
    source = Path(source)
    destination = Path(destination)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == destination.resolve():
        raise ValueError("Refusing to overwrite source MIDI")

    data = bytearray(source.read_bytes())
    if data[:4] != b"MThd":
        raise ValueError(f"Not a Standard MIDI File: {source.name}")

    repairs: list[MidiRepair] = []
    marker = b"\xff\x59\x02"
    cursor = 0
    while True:
        index = data.find(marker, cursor)
        if index < 0:
            break
        value_index = index + len(marker)
        if value_index + 1 >= len(data):
            raise ValueError(f"Truncated key-signature event in {source.name}")
        sharps_flats = struct.unpack("b", bytes([data[value_index]]))[0]
        mode = data[value_index + 1]
        if mode not in (0, 1):
            # Invalid mode is metadata too; normalize to major rather than blocking notes.
            repairs.append(MidiRepair(value_index + 1, "key_signature_mode", mode, 0))
            data[value_index + 1] = 0
        if not -7 <= sharps_flats <= 7:
            replacement = max(-7, min(7, sharps_flats))
            repairs.append(MidiRepair(value_index, "key_signature_accidentals", sharps_flats, replacement))
            data[value_index] = struct.pack("b", replacement)[0]
        cursor = value_index + 2

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return repairs


def repairs_to_dict(repairs: list[MidiRepair]) -> list[dict]:
    return [asdict(item) for item in repairs]
