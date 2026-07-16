from __future__ import annotations

import math

import numpy as np
import pandas as pd

EPSILON = 1e-9


def robust_median(values: pd.Series | np.ndarray | list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    return float(np.median(arr))


def robust_mad(values: pd.Series | np.ndarray | list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return EPSILON
    med = np.median(arr)
    mad = np.median(np.abs(arr - med))
    return float(max(mad, EPSILON))


def robust_z_series(values: pd.Series) -> pd.Series:
    med = robust_median(values)
    mad = robust_mad(values)
    return (values.astype(float) - med) / mad


def clamp01(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))
