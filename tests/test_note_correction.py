import numpy as np
from engine.note_correction import compare_note_content


def test_detects_missing_and_extra_pitch_classes():
    times = np.array([0.0, 0.1, 0.2])
    chroma = np.zeros((12, 3))
    chroma[0, :] = 1.0
    chroma[4, :] = 0.8
    events = [(0.05, 0), (0.05, 7)]
    result = compare_note_content(events, chroma, times, window_seconds=.25, audio_threshold_ratio=.55)
    first = result[0]
    assert 4 in first.missing_pitch_classes
    assert 7 in first.extra_pitch_classes
    assert 0 in first.matched_pitch_classes


def test_matching_note_content_passes():
    times = np.array([0.0, 0.1])
    chroma = np.zeros((12, 2))
    chroma[2, :] = 1.0
    events = [(0.05, 2)]
    result = compare_note_content(events, chroma, times, window_seconds=.25, audio_threshold_ratio=.55)
    assert result[0].action == "match"
