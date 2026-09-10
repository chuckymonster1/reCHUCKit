import numpy as np
import pytest
from engine.chord_engine import compare_chord_windows


def test_matching_triad_scores_as_match():
    times = np.array([0.0, 0.1, 0.2, 0.3])
    chroma = np.zeros((12, 4))
    chroma[[0,4,7], :] = 1.0
    events = [(0.05,0),(0.05,4),(0.05,7)]
    result = compare_chord_windows(events, chroma, times, window_seconds=.5, top_n=3)
    assert result[0].overlap_score == 1.0
    assert result[0].action == "match"


def test_bad_shape_is_rejected():
    with pytest.raises(ValueError):
        compare_chord_windows([], np.zeros((11, 2)), np.array([0.0, .1]))


def test_empty_timeline_returns_empty():
    assert compare_chord_windows([], np.zeros((12,0)), np.array([])) == []
