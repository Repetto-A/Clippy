from video_clipper.config import WebcamRegion
from video_clipper.reframe import _median_region


def test_median_region_averages_each_axis():
    regions = [
        WebcamRegion(x=0.70, y=0.38, w=0.24, h=0.22),
        WebcamRegion(x=0.74, y=0.40, w=0.26, h=0.24),
        WebcamRegion(x=0.78, y=0.42, w=0.28, h=0.26),
    ]
    med = _median_region(regions)
    assert med.x == 0.74
    assert med.y == 0.4
    assert med.w == 0.26
    assert med.h == 0.24
