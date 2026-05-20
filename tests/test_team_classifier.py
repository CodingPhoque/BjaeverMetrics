import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fodbold.team.team_classifier import TeamClassifier  # noqa: E402


def test_team_classifier_fits_and_predicts_two_teams():
    features = np.array(
        [
            [60, 135, 105],
            [62, 136, 106],
            [64, 134, 104],
            [116, 146, 142],
            [118, 147, 143],
            [120, 145, 141],
        ],
        dtype=np.float32,
    )

    classifier = TeamClassifier(min_fit_samples=4, random_state=0)
    classifier.fit(features)

    dark_team = classifier.predict(np.array([61, 135, 105], dtype=np.float32))
    orange_team = classifier.predict(np.array([119, 146, 142], dtype=np.float32))

    assert classifier.is_fitted
    assert dark_team in {"team_a", "team_b"}
    assert orange_team in {"team_a", "team_b"}
    assert dark_team != orange_team


def test_predict_requires_fit_first():
    classifier = TeamClassifier(min_fit_samples=2)

    try:
        classifier.predict(np.array([60, 135, 105], dtype=np.float32))
    except RuntimeError as error:
        assert "must be fitted" in str(error)
    else:
        raise AssertionError("Expected RuntimeError")


def test_fit_requires_enough_samples():
    classifier = TeamClassifier(min_fit_samples=4)

    try:
        classifier.fit(np.array([[60, 135, 105], [116, 146, 142]], dtype=np.float32))
    except ValueError as error:
        assert "Need at least 4 features" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_fit_requires_three_value_features():
    classifier = TeamClassifier(min_fit_samples=2)

    try:
        classifier.fit(np.array([[1, 2], [3, 4]], dtype=np.float32))
    except ValueError as error:
        assert "shape (n, 3)" in str(error)
    else:
        raise AssertionError("Expected ValueError")
