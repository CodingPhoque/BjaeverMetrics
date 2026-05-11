from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans


class TeamClassifier:
    """Learns two team color clusters and predicts team labels from jersey features."""
    def __init__(self, min_fit_samples: int = 50, random_state: int = 0):
        """Create a KMeans classifier for two teams."""
        self.min_fit_samples = min_fit_samples
        self.model = KMeans(n_clusters=2, n_init=10, random_state=random_state)

    @property
    def is_fitted(self) -> bool:
        """Return True when KMeans has learned cluster centers."""
        return hasattr(self.model, "cluster_centers_")

    def fit(self, features: np.ndarray) -> None:
        """Learn two team color clusters from jersey features shaped as (n, 3)."""
        features = np.asarray(features, dtype=np.float32)

        if features.ndim != 2 or features.shape[1] != 3:
            raise ValueError(f"Expected features with shape (n, 3), got {features.shape}")

        if len(features) < self.min_fit_samples:
            raise ValueError(
                f"Need at least {self.min_fit_samples} features, got {len(features)}"
            )

        self.model.fit(features)

    def predict(self, feature: np.ndarray) -> str:
        """Predict team_a or team_b for one jersey feature shaped as (3,)."""
        if not self.is_fitted:
            raise RuntimeError("TeamClassifier must be fitted before predict().")

        feature = np.asarray(feature, dtype=np.float32)
        if feature.shape != (3,):
            raise ValueError(f"Expected feature with shape (3,), got {feature.shape}")

        cluster_id = int(self.model.predict(feature.reshape(1, -1))[0])
        return "team_a" if cluster_id == 0 else "team_b"
