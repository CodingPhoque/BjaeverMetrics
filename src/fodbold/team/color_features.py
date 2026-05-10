from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(slots=True)
class JerseyColorConfig:
    x_margin_ratio: float = 0.20
    y_start_ratio: float = 0.20
    y_end_ratio: float = 0.65
    min_pixels: int = 20
    grass_hsv_lower: tuple[int, int, int] = (35, 40, 40)
    grass_hsv_upper: tuple[int, int, int] = (90, 255, 255)


def extract_jersey_color(
    frame: np.ndarray,
    bbox_xyxy: tuple[float, float, float, float],
    config: JerseyColorConfig | None = None,
) -> np.ndarray | None:
    config = config or JerseyColorConfig()
    crop = crop_jersey_region(frame, bbox_xyxy, config)
    if crop is None:
        return None

    return extract_lab_feature_without_grass(crop, config)


def crop_jersey_region(
    frame: np.ndarray,
    bbox_xyxy: tuple[float, float, float, float],
    config: JerseyColorConfig | None = None,
) -> np.ndarray | None:
    config = config or JerseyColorConfig()
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox_xyxy

    x1 = int(np.clip(round(x1), 0, width - 1))
    x2 = int(np.clip(round(x2), 0, width - 1))
    y1 = int(np.clip(round(y1), 0, height - 1))
    y2 = int(np.clip(round(y2), 0, height - 1))

    box_width = x2 - x1
    box_height = y2 - y1
    if box_width < 4 or box_height < 8:
        return None

    crop_x1 = x1 + int(box_width * config.x_margin_ratio)
    crop_x2 = x2 - int(box_width * config.x_margin_ratio)
    crop_y1 = y1 + int(box_height * config.y_start_ratio)
    crop_y2 = y1 + int(box_height * config.y_end_ratio)

    if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
        return None

    return frame[crop_y1:crop_y2, crop_x1:crop_x2].copy()


def extract_lab_feature_without_grass(
    crop_bgr: np.ndarray,
    config: JerseyColorConfig | None = None,
) -> np.ndarray | None:
    config = config or JerseyColorConfig()
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)

    grass_lower = np.array(config.grass_hsv_lower, dtype=np.uint8)
    grass_upper = np.array(config.grass_hsv_upper, dtype=np.uint8)
    grass_mask = cv2.inRange(hsv, grass_lower, grass_upper) > 0
    keep_mask = ~grass_mask

    if int(np.count_nonzero(keep_mask)) < config.min_pixels:
        return None

    lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
    return np.median(lab[keep_mask], axis=0).astype(np.float32)
