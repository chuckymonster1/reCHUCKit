import pytest

from engine.pitch_engine import compare_pitch_centers, dominant_pitch_class


def test_dominant_pitch_class():
    hist = [0.0] * 12
    hist[9] = 1.0
    assert dominant_pitch_class(hist) == 9


def test_matching_pitch_center():
    midi = [0.0] * 12
    midi[0] = 1.0
    audio = [0.0] * 12
    audio[0] = 0.8
    audio[7] = 0.2
    result = compare_pitch_centers(midi, audio)
    assert result.semitone_delta == 0
    assert result.action == "match"


def test_uncertain_transpose_requires_review():
    midi = [0.0] * 12
    midi[0] = 1.0
    audio = [0.0] * 12
    audio[2] = 0.40
    audio[9] = 0.35
    result = compare_pitch_centers(midi, audio)
    assert result.semitone_delta == 2
    assert result.action == "review"


def test_invalid_histogram_rejected():
    with pytest.raises(ValueError):
        compare_pitch_centers([1.0], [0.0] * 12)
