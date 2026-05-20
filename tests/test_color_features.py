import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fodbold.team.color_features import (  # noqa: E402
    JerseyColorConfig,
    crop_jersey_region,
    extract_jersey_color,
)


def test_extract_jersey_color_returns_lab_feature_for_colored_box():
    frame = np.full((100, 60, 3), (0, 128, 0), dtype=np.uint8)
    frame[20:65, 12:48] = (255, 0, 0)

    feature = extract_jersey_color(
        frame,
        (0, 0, 60, 100),
        JerseyColorConfig(x_margin_ratio=0.20, y_start_ratio=0.20, y_end_ratio=0.65),
    )

    expected_lab = cv2.cvtColor(np.uint8([[[255, 0, 0]]]), cv2.COLOR_BGR2LAB)[0, 0]
    assert feature is not None
    np.testing.assert_allclose(feature, expected_lab, atol=1)


def test_extract_jersey_color_filters_green_grass_pixels():
    frame = np.full((100, 60, 3), (0, 128, 0), dtype=np.uint8)
    frame[20:65, 12:30] = (0, 128, 0)
    frame[20:65, 30:48] = (0, 140, 255)

    feature = extract_jersey_color(frame, (0, 0, 60, 100))

    orange_lab = cv2.cvtColor(np.uint8([[[0, 140, 255]]]), cv2.COLOR_BGR2LAB)[0, 0]
    grass_lab = cv2.cvtColor(np.uint8([[[0, 128, 0]]]), cv2.COLOR_BGR2LAB)[0, 0]
    assert feature is not None
    assert np.linalg.norm(feature - orange_lab) < np.linalg.norm(feature - grass_lab)


def test_extract_jersey_color_returns_none_when_only_grass_remains():
    frame = np.full((100, 60, 3), (0, 128, 0), dtype=np.uint8)

    feature = extract_jersey_color(frame, (0, 0, 60, 100))

    assert feature is None


def test_crop_jersey_region_uses_configured_bbox_ratios():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    crop = crop_jersey_region(
        frame,
        (10, 20, 90, 100),
        JerseyColorConfig(x_margin_ratio=0.25, y_start_ratio=0.25, y_end_ratio=0.75),
    )

    assert crop is not None
    assert crop.shape == (40, 40, 3)
