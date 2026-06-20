from video_clipper.rubric import combine_score


def test_equal_weights_average():
    assert combine_score(100, 0, 0, 0, weights=(0.25, 0.25, 0.25, 0.25)) == 25.0
    assert combine_score(80, 80, 80, 80, weights=(0.25, 0.25, 0.25, 0.25)) == 80.0


def test_custom_weights_honored():
    assert combine_score(90, 10, 10, 10, weights=(1.0, 0.0, 0.0, 0.0)) == 90.0


def test_clamps_to_0_100():
    assert combine_score(200, 200, 200, 200, weights=(1, 1, 1, 1)) == 100.0
    assert combine_score(-50, 0, 0, 0, weights=(1, 0, 0, 0)) == 0.0
