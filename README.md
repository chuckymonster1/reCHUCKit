# reCHUCKit

**Song ReCreation Engine**

reCHUCKit rebuilds AI-generated or reference productions into cleaner, editable music-production assets.

## Core workflow
1. Upload the full reference mix.
2. Upload isolated stems when available.
3. Upload MIDI extracted from Suno or another source.
4. Analyze tempo, key, structure, instrument roles, note timing, velocity, and MIDI quality.
5. Clean and rebuild MIDI while preserving human feel.
6. Compare the reconstruction against the reference audio.
7. Export cleaned MIDI and production guidance for DAW reconstruction.

## Design rule
Audio is the truth. MIDI is the editable skeleton. reCHUCKit uses both instead of blindly trusting extracted MIDI.

## MVP
- Reference audio input
- Multiple stem inputs
- Multiple MIDI inputs
- MIDI cleanup controls
- Instrument-role mapping
- Reconstruction report
- Clean MIDI export

## Roadmap
- Stem-to-MIDI quality scoring
- Audio/MIDI alignment
- Drum note remapping
- Chord and bass correction
- Patch/instrument recommendations
- Arrangement/section detection
- Logic Pro-focused export workflow
- Iterative reference matching
