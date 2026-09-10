# reCHUCKit

**Song ReCreation Engine**

reCHUCKit turns reference audio, stems, and extracted MIDI into cleaner, editable, DAW-ready reconstruction assets.

> **Design rule:** Audio is the truth. MIDI is the editable skeleton.

## V1 workflow

1. Upload a reference mix, stems, MIDI, or any useful combination.
2. Analyze reference/stem tempo, onset timing, pitch-class content, duration, and level.
3. Inspect MIDI note content, timing, velocity, role, and drum-channel behavior.
4. Clean MIDI non-destructively while preserving note durations and musical feel.
5. Repair obvious micro-notes and soften only extreme velocity outliers.
6. Classify likely musical roles with confidence and evidence instead of pretending MIDI contains timbre.
7. Produce transparent structural similarity scores when reference audio and melodic MIDI are both present.
8. Package corrected MIDI, source stems, reference audio, session report, and Logic/Reason import instructions into a ZIP.

## What V1 does now

- Real browser-to-backend processing through the **READY? reCHUCKit** button
- Reference audio input
- Multiple stem inputs
- Multiple MIDI inputs
- Adjustable groove preservation, timing cleanup, and velocity cleanup
- MIDI note-on/note-off pairing and duration-preserving timing correction
- Ultra-short-note repair
- Velocity-outlier correction without flattening normal dynamics
- Confidence-scored role detection
- General MIDI drum-family analysis for kicks, snares, hats, toms, cymbals, and percussion
- Structural reference scoring for tempo, pitch-class similarity, and onset coverage
- Original-file overwrite protection
- DAW-neutral Logic Pro / Reason ZIP export
- Machine-readable session report
- FastAPI backend
- Docker deployment support
- GitHub Actions lint + automated tests

## Safety / accuracy boundaries

reCHUCKit does **not** claim that MIDI contains the original instrument sound. V1 does not synthesize a finished reconstructed WAV and does not generate native `.logicx` or Reason project files.

Pitch, chord, and surgical note-correction engines exist in the codebase, but automatic pitch rewriting remains intentionally review-gated until the audio evidence is strong enough to make those edits safely. Drum MIDI is never treated like pitched melodic MIDI.

Structural similarity scores are exactly that: **structural**. They do not claim to measure instrument tone, mix, effects, articulation, vocal identity, or mastering similarity.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
uvicorn server:app --reload
```

Open `http://127.0.0.1:8000`.

## Docker

```bash
docker build -t rechuckit .
docker run --rm -p 8000:8000 rechuckit
```

Open `http://127.0.0.1:8000`.

## Export package

A completed session can contain:

```text
<song>_reCHUCKit_EXPORT/
├── MIDI/
│   └── *_reCHUCKit.mid
├── WAV_STEMS/
├── REFERENCE/
├── DOCS/
│   └── IMPORT_GUIDE.txt
└── session.json
```

The app also creates a downloadable `<song>_reCHUCKit.zip` package.

## Architecture

- `server.py` — web API, upload validation, session orchestration, download endpoint
- `engine/audio_analyzer.py` — measurable audio-reference features
- `engine/midi_engine.py` — non-destructive MIDI cleanup
- `engine/role_engine.py` — confidence-scored MIDI role detection
- `engine/drum_engine.py` — percussion-specific analysis
- `engine/scoring.py` — transparent structural reconstruction score
- `engine/alignment.py` — audio/MIDI onset comparison proposals
- `engine/pitch_engine.py` — pitch comparison proposals
- `engine/chord_engine.py` — chord-window comparison proposals
- `engine/note_correction.py` — note-content proposals
- `engine/correction_engine.py` — reviewed correction application
- `engine/exporter.py` — Logic/Reason-ready portable session packaging

## Next-generation target

The next layer is true sound matching: render candidate instruments/patches, compare those renders against isolated stems, score the result, and iterate toward the reference while keeping every automated decision inspectable and reversible.
