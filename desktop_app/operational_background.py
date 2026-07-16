from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Sequence

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from desktop_app.theme import family_theme_tokens, normalize_family_theme


DEFAULT_BACKGROUND_MODE = "default"
DEFAULT_BACKGROUND_INTENSITY = "low"
DEFAULT_BACKGROUND_MOTION = "smooth"

BACKGROUND_MODE_LABELS: dict[str, str] = {
    "default": "Padrao",
    "tesla": "Nikola Tesla",
}

BACKGROUND_INTENSITY_LABELS: dict[str, str] = {
    "low": "Baixa",
    "medium": "Media",
}

BACKGROUND_MOTION_LABELS: dict[str, str] = {
    "smooth": "Suave",
    "very_smooth": "Muito suave",
}


def normalize_background_mode(mode_name: str | None) -> str:
    candidate = str(mode_name or "").strip().lower()
    if candidate in BACKGROUND_MODE_LABELS:
        return candidate
    return DEFAULT_BACKGROUND_MODE


def available_background_modes() -> dict[str, str]:
    return dict(BACKGROUND_MODE_LABELS)


def normalize_background_intensity(level: str | None) -> str:
    candidate = str(level or "").strip().lower()
    if candidate in BACKGROUND_INTENSITY_LABELS:
        return candidate
    return DEFAULT_BACKGROUND_INTENSITY


def available_background_intensities() -> dict[str, str]:
    return dict(BACKGROUND_INTENSITY_LABELS)


def normalize_background_motion(level: str | None) -> str:
    candidate = str(level or "").strip().lower()
    if candidate in BACKGROUND_MOTION_LABELS:
        return candidate
    return DEFAULT_BACKGROUND_MOTION


def available_background_motion_profiles() -> dict[str, str]:
    return dict(BACKGROUND_MOTION_LABELS)


@dataclass(frozen=True)
class TeslaVisualProfile:
    intensity: float
    pulse_speed: float
    line_density: float
    glow_intensity: float
    opacity: float


def _tesla_profile(intensity_key: str, motion_key: str, operational_state: str) -> TeslaVisualProfile:
    base_intensity = {
        "low": {"intensity": 0.40, "line_density": 0.42, "glow": 0.22, "opacity": 0.12},
        "medium": {"intensity": 0.58, "line_density": 0.58, "glow": 0.30, "opacity": 0.17},
    }[normalize_background_intensity(intensity_key)]
    speed = {
        "smooth": 0.0135,
        "very_smooth": 0.009,
    }[normalize_background_motion(motion_key)]
    state_factor = {
        "idle": 0.88,
        "active": 1.0,
        "busy": 1.22,
        "degraded": 0.60,
    }.get(str(operational_state or "").strip().lower(), 1.0)
    return TeslaVisualProfile(
        intensity=base_intensity["intensity"] * state_factor,
        pulse_speed=speed * state_factor,
        line_density=base_intensity["line_density"],
        glow_intensity=base_intensity["glow"] * state_factor,
        opacity=base_intensity["opacity"] * min(state_factor, 1.18),
    )


class OperationalBackgroundLayer(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        theme_name: str = "midnight",
        background_mode: str = DEFAULT_BACKGROUND_MODE,
        intensity_key: str = DEFAULT_BACKGROUND_INTENSITY,
        motion_key: str = DEFAULT_BACKGROUND_MOTION,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAutoFillBackground(False)

        self._theme_name = normalize_family_theme(theme_name)
        self._background_mode = normalize_background_mode(background_mode)
        self._intensity_key = normalize_background_intensity(intensity_key)
        self._motion_key = normalize_background_motion(motion_key)
        self._operational_state = "idle"
        self._segments: list[tuple[QPointF, QPointF, float]] = []
        self._nodes: list[QPointF] = []
        self._phase = 0.0
        self._activity_impulse = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(66)
        self._timer.timeout.connect(self._advance_animation)

        self._rebuild_mesh()
        self._update_animation_state()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(1680, 960)

    def set_theme(self, theme_name: str) -> None:
        self._theme_name = normalize_family_theme(theme_name)
        self.update()

    def set_background_mode(self, background_mode: str) -> None:
        resolved = normalize_background_mode(background_mode)
        if resolved == self._background_mode:
            return
        self._background_mode = resolved
        self._update_animation_state()
        self.update()

    def set_intensity_level(self, intensity_key: str) -> None:
        self._intensity_key = normalize_background_intensity(intensity_key)
        self._rebuild_mesh()
        self.update()

    def set_motion_profile(self, motion_key: str) -> None:
        self._motion_key = normalize_background_motion(motion_key)
        self._update_animation_state()
        self.update()

    def set_operational_state(self, operational_state: str) -> None:
        normalized = str(operational_state or "").strip().lower() or "idle"
        if normalized not in {"idle", "active", "busy", "degraded"}:
            normalized = "idle"
        self._operational_state = normalized
        self._update_animation_state()
        self.update()

    def pulse_activity(self, strength: float = 0.22) -> None:
        self._activity_impulse = min(1.0, self._activity_impulse + max(0.0, float(strength)))
        if self._background_mode == "tesla":
            self.update()

    def current_background_mode(self) -> str:
        return self._background_mode

    def current_intensity_level(self) -> str:
        return self._intensity_key

    def current_motion_profile(self) -> str:
        return self._motion_key

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._rebuild_mesh()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect())
        if rect.width() <= 0 or rect.height() <= 0:
            return

        tokens = family_theme_tokens(self._theme_name)
        self._paint_base(painter, rect, tokens)
        if self._background_mode != "tesla":
            return

        profile = _tesla_profile(self._intensity_key, self._motion_key, self._operational_state)
        self._paint_mesh(painter, rect, tokens, profile)
        self._paint_energy(painter, tokens, profile)

    def _paint_base(self, painter: QPainter, rect: QRectF, tokens: dict[str, str]) -> None:
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(tokens["bg_canvas"]))
        grad.setColorAt(0.60, QColor(tokens["bg_frame"]))
        grad.setColorAt(1.0, QColor(tokens["bg_canvas"]))
        painter.fillRect(rect, grad)

        vignette = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.72)
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.72, QColor(3, 10, 18, 0))
        vignette.setColorAt(1.0, QColor(3, 10, 18, 72))
        painter.fillRect(rect, vignette)

    def _paint_mesh(
        self,
        painter: QPainter,
        rect: QRectF,
        tokens: dict[str, str],
        profile: TeslaVisualProfile,
    ) -> None:
        del rect
        line_color = QColor(tokens["accent_primary"])
        line_color.setAlphaF(min(0.22, profile.opacity))
        pen = QPen(line_color, 1.05)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        for start, end, _length in self._segments:
            painter.drawLine(start, end)

        node_color = QColor(tokens["accent_bright"])
        base_alpha = 34 if self._operational_state != "degraded" else 18
        for idx, node in enumerate(self._nodes):
            alpha = base_alpha + int((math.sin(self._phase + (idx * 0.37)) + 1.0) * 8.0 * profile.glow_intensity)
            glow = QRadialGradient(node, 16.0)
            glow.setColorAt(0.0, QColor(node_color.red(), node_color.green(), node_color.blue(), alpha))
            glow.setColorAt(0.35, QColor(node_color.red(), node_color.green(), node_color.blue(), alpha // 2))
            glow.setColorAt(1.0, QColor(node_color.red(), node_color.green(), node_color.blue(), 0))
            painter.fillRect(QRectF(node.x() - 16.0, node.y() - 16.0, 32.0, 32.0), glow)

    def _paint_energy(self, painter: QPainter, tokens: dict[str, str], profile: TeslaVisualProfile) -> None:
        if not self._segments:
            return
        pulse_count = max(4, min(11, int(5 + len(self._segments) * 0.04)))
        base_glow = QColor(tokens["accent_bright"])
        tail_color = QColor(tokens["accent_primary"])
        for idx in range(pulse_count):
            segment_index = (idx * 11 + int(self._phase * 13.0)) % len(self._segments)
            start, end, length = self._segments[segment_index]
            if length <= 0.0:
                continue
            progress = (self._phase * (0.18 + idx * 0.013) + idx * 0.21 + self._activity_impulse * 0.08) % 1.0
            x = start.x() + (end.x() - start.x()) * progress
            y = start.y() + (end.y() - start.y()) * progress
            pulse_center = QPointF(x, y)

            painter.setPen(Qt.PenStyle.NoPen)
            glow = QRadialGradient(pulse_center, 17.0)
            glow_alpha = 52 + int(48.0 * min(1.0, profile.glow_intensity + self._activity_impulse * 0.15))
            glow.setColorAt(0.0, QColor(base_glow.red(), base_glow.green(), base_glow.blue(), glow_alpha))
            glow.setColorAt(0.42, QColor(base_glow.red(), base_glow.green(), base_glow.blue(), glow_alpha // 2))
            glow.setColorAt(1.0, QColor(base_glow.red(), base_glow.green(), base_glow.blue(), 0))
            painter.fillRect(QRectF(x - 17.0, y - 17.0, 34.0, 34.0), glow)

            tail_pen = QPen(tail_color, 1.7)
            tail_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            tail_pen.setColor(QColor(tail_color.red(), tail_color.green(), tail_color.blue(), 136))
            painter.setPen(tail_pen)
            tail_scale = min(18.0, length * 0.22)
            tail_start = QPointF(
                x - (end.x() - start.x()) / max(length, 1.0) * tail_scale,
                y - (end.y() - start.y()) / max(length, 1.0) * tail_scale,
            )
            painter.drawLine(tail_start, pulse_center)

    def _advance_animation(self) -> None:
        if self._background_mode != "tesla":
            return
        profile = _tesla_profile(self._intensity_key, self._motion_key, self._operational_state)
        self._phase = (self._phase + profile.pulse_speed + self._activity_impulse * 0.01) % (math.pi * 8.0)
        self._activity_impulse = max(0.0, self._activity_impulse * 0.94)
        self.update()

    def _update_animation_state(self) -> None:
        if self._background_mode == "tesla":
            if not self._timer.isActive():
                interval = 72 if self._motion_key == "very_smooth" else 56
                self._timer.start(interval)
        else:
            self._timer.stop()

    def _rebuild_mesh(self) -> None:
        width = max(1, self.width())
        height = max(1, self.height())
        rect = QRectF(0.0, 0.0, float(width), float(height))
        density = _tesla_profile(self._intensity_key, self._motion_key, self._operational_state).line_density
        cols = max(6, min(11, int(6 + density * width / 250.0)))
        rows = max(4, min(8, int(4 + density * height / 210.0)))
        left = 28.0
        right = max(left + 100.0, rect.width() - 28.0)
        top = 24.0
        bottom = max(top + 120.0, rect.height() - 24.0)
        rng = random.Random((width * 73856093) ^ (height * 19349663))

        xs = [left + ((right - left) / max(1, cols - 1)) * index for index in range(cols)]
        ys = [top + ((bottom - top) / max(1, rows - 1)) * index for index in range(rows)]
        nodes: list[list[QPointF]] = []
        for row_index, base_y in enumerate(ys):
            row_nodes: list[QPointF] = []
            for col_index, base_x in enumerate(xs):
                jitter_x = rng.uniform(-10.0, 10.0) * (0.75 if 0 < col_index < cols - 1 else 0.15)
                jitter_y = rng.uniform(-10.0, 10.0) * (0.75 if 0 < row_index < rows - 1 else 0.15)
                row_nodes.append(QPointF(base_x + jitter_x, base_y + jitter_y))
            nodes.append(row_nodes)

        segments: list[tuple[QPointF, QPointF, float]] = []
        for row_index in range(rows):
            for col_index in range(cols):
                point = nodes[row_index][col_index]
                if col_index + 1 < cols and rng.random() <= (0.84 + density * 0.08):
                    right_point = nodes[row_index][col_index + 1]
                    segments.append((point, right_point, self._distance(point, right_point)))
                if row_index + 1 < rows and rng.random() <= (0.66 + density * 0.12):
                    bottom_point = nodes[row_index + 1][col_index]
                    segments.append((point, bottom_point, self._distance(point, bottom_point)))

        self._segments = segments
        candidate_nodes: list[QPointF] = []
        for row_index, row_nodes in enumerate(nodes):
            for col_index, node in enumerate(row_nodes):
                if (row_index + col_index) % 2 == 0:
                    candidate_nodes.append(node)
        self._nodes = candidate_nodes[: max(8, min(len(candidate_nodes), 24))]

    @staticmethod
    def _distance(start: QPointF, end: QPointF) -> float:
        return math.hypot(end.x() - start.x(), end.y() - start.y())
