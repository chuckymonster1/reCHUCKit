from engine.alignment import compare_onsets


def test_exact_onset_is_safe_snap():
    result = compare_onsets([1.0], [1.0])
    assert result[0].confidence == 1.0
    assert result[0].action == "safe-snap"


def test_far_onset_is_left_untouched():
    result = compare_onsets([1.0], [1.25], tolerance_seconds=0.08)
    assert result[0].confidence == 0.0
    assert result[0].action == "leave"


def test_borderline_match_requires_review():
    result = compare_onsets([1.0], [1.02], tolerance_seconds=0.08, auto_threshold=.90)
    assert result[0].action == "review"


def test_no_audio_onsets_makes_no_proposals():
    assert compare_onsets([1.0, 2.0], []) == []
