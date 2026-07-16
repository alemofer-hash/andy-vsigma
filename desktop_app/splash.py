from __future__ import annotations

import math
import time

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget

from andy_version import APP_NAME
from desktop_app.theme import family_theme_tokens


class AndySplashScreen(QWidget):
    def __init__(self, *, min_visible_ms: int = 260) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._tokens = family_theme_tokens()
        self._min_visible_ms = max(0, int(min_visible_ms))
        self._shown_at = 0.0
        self._progress_value = 0.0
        self._pulse_phase = 0.0
        self._closing = False
        self._fade_animation: QPropertyAnimation | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedSize(760, 430)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(28)
        self._pulse_timer.timeout.connect(self._advance_pulse)

        self._build_ui()
        self._center_on_primary_screen()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(760, 430)

    def _build_ui(self) -> None:
        content = QVBoxLayout(self)
        content.setContentsMargins(74, 62, 74, 54)
        content.setSpacing(12)

        self.eyebrow_label = QLabel("ANDY FAMILY SYSTEMS")
        self.eyebrow_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                color: #73dcff;
                font-family: "Bahnschrift SemiBold";
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.24em;
            }
            """
        )
        content.addWidget(self.eyebrow_label)

        self.title_label = QLabel("IGNICAO BLINDADA")
        self.title_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                color: #f3f7fb;
                font-family: "Bahnschrift SemiBold";
                font-size: 30px;
                font-weight: 700;
            }
            """
        )
        content.addWidget(self.title_label)

        self.subtitle_label = QLabel(
            "Inicializando inteligencia operacional, runtime local e cockpit de consulta sem perder densidade tecnica."
        )
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setMaximumWidth(430)
        self.subtitle_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                color: #afc0d4;
                font-size: 14px;
                line-height: 1.35;
            }
            """
        )
        content.addWidget(self.subtitle_label)
        content.addSpacing(18)

        self.stage_label = QLabel("Aquecendo runtime blindado")
        self.stage_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                color: #c7d4e3;
                font-family: "Bahnschrift SemiBold";
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.08em;
            }
            """
        )
        content.addWidget(self.stage_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(16)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background: rgba(8, 16, 28, 0.92);
                border: 1px solid #22364d;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #23c7ff,
                    stop:0.65 #73dcff,
                    stop:1 #1187c7
                );
            }
            """
        )
        content.addWidget(self.progress_bar)

        self.footer_label = QLabel("Boot real em andamento")
        self.footer_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                color: #7b90a8;
                font-size: 12px;
            }
            """
        )
        content.addWidget(self.footer_label)
        content.addStretch(1)

        self.signature_label = QLabel(APP_NAME)
        self.signature_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                color: #73dcff;
                font-family: "Bahnschrift SemiBold";
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 0.08em;
            }
            """
        )
        content.addWidget(self.signature_label, alignment=Qt.AlignmentFlag.AlignLeft)

    def _center_on_primary_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        self.move(
            geometry.center().x() - (self.width() // 2),
            geometry.center().y() - (self.height() // 2),
        )

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._shown_at = time.monotonic()
        self._pulse_timer.start()
        super().showEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._pulse_timer.stop()
        super().closeEvent(event)

    def set_stage(self, label: str, *, progress: float | None = None, footer: str | None = None) -> None:
        self.stage_label.setText(str(label).strip())
        if progress is not None:
            clamped = max(0.0, min(1.0, float(progress)))
            self._progress_value = clamped
            self.progress_bar.setValue(int(round(clamped * 100.0)))
        if footer is not None:
            self.footer_label.setText(str(footer).strip())
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def show_error(self, detail: str) -> None:
        self.stage_label.setText("Falha na ignicao")
        self.footer_label.setText(str(detail).strip())
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background: rgba(8, 16, 28, 0.92);
                border: 1px solid #4a2228;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff6c77,
                    stop:1 #cf4452
                );
            }
            """
        )
        self.update()

    def finish(self) -> None:
        if self._closing:
            return
        self._closing = True
        remaining_ms = self._min_visible_ms - int((time.monotonic() - self._shown_at) * 1000.0)
        if remaining_ms > 0:
            QTimer.singleShot(remaining_ms, self._begin_fade_out)
            return
        self._begin_fade_out()

    def _begin_fade_out(self) -> None:
        app = QApplication.instance()
        if app is not None and app.platformName().lower() == "offscreen":
            self.close()
            return
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setDuration(240)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_animation.finished.connect(self.close)
        self._fade_animation.start()

    def _advance_pulse(self) -> None:
        self._pulse_phase = (self._pulse_phase + 0.055) % (math.pi * 2.0)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        full_rect = QRectF(self.rect())
        panel_rect = full_rect.adjusted(18.0, 18.0, -18.0, -18.0)

        glow = QRadialGradient(panel_rect.center(), panel_rect.width() * 0.62)
        glow.setColorAt(0.0, QColor(35, 199, 255, 48))
        glow.setColorAt(0.52, QColor(17, 135, 199, 16))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)

        shell_path = QPainterPath()
        shell_path.addRoundedRect(panel_rect, 28.0, 28.0)
        shell_grad = QLinearGradient(panel_rect.topLeft(), panel_rect.bottomRight())
        shell_grad.setColorAt(0.0, QColor("#07101a"))
        shell_grad.setColorAt(0.55, QColor(self._tokens["bg_frame"]))
        shell_grad.setColorAt(1.0, QColor("#0d2138"))
        painter.fillPath(shell_path, shell_grad)

        inner_rect = panel_rect.adjusted(10.0, 10.0, -10.0, -10.0)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 22.0, 22.0)
        inner_grad = QLinearGradient(inner_rect.topLeft(), inner_rect.bottomRight())
        inner_grad.setColorAt(0.0, QColor("#08111c"))
        inner_grad.setColorAt(0.5, QColor(self._tokens["bg_frame"]))
        inner_grad.setColorAt(1.0, QColor("#071a2b"))
        painter.fillPath(inner_path, inner_grad)

        border_pen = QPen(QColor(self._tokens["border_glow"]))
        border_pen.setWidthF(1.35)
        border_pen.setColor(QColor(46, 174, 232, 170))
        painter.setPen(border_pen)
        painter.drawRoundedRect(inner_rect, 22.0, 22.0)

        painter.setPen(QPen(QColor(115, 220, 255, 72), 1.0))
        for offset in (74.0, 92.0, 110.0):
            painter.drawLine(
                QPointF(inner_rect.left() + 36.0, inner_rect.top() + offset),
                QPointF(inner_rect.left() + 286.0, inner_rect.top() + offset),
            )

        painter.setPen(QPen(QColor(115, 220, 255, 58), 1.0))
        painter.drawLine(
            QPointF(inner_rect.left() + 30.0, inner_rect.bottom() - 60.0),
            QPointF(inner_rect.right() - 30.0, inner_rect.bottom() - 60.0),
        )

        orb_rect = QRectF(inner_rect.right() - 228.0, inner_rect.top() + 46.0, 170.0, 170.0)
        orb = QRadialGradient(orb_rect.center(), orb_rect.width() * 0.56)
        pulse_alpha = 86 + int((math.sin(self._pulse_phase) + 1.0) * 18.0)
        orb.setColorAt(0.0, QColor(35, 199, 255, pulse_alpha))
        orb.setColorAt(0.35, QColor(17, 135, 199, 66))
        orb.setColorAt(0.7, QColor(9, 24, 40, 12))
        orb.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(orb)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(orb_rect)

        ring_pen = QPen(QColor(115, 220, 255, 118))
        ring_pen.setWidthF(1.1)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(orb_rect.adjusted(8.0, 8.0, -8.0, -8.0))

        self._paint_rocket(painter, orb_rect.adjusted(34.0, 22.0, -34.0, -14.0))

    def _paint_rocket(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        body = QPainterPath()
        nose = QPointF(rect.center().x(), rect.top())
        left_shoulder = QPointF(rect.left() + rect.width() * 0.34, rect.top() + rect.height() * 0.28)
        left_body = QPointF(rect.left() + rect.width() * 0.38, rect.top() + rect.height() * 0.78)
        left_fin = QPointF(rect.left() + rect.width() * 0.14, rect.top() + rect.height() * 0.88)
        tail = QPointF(rect.center().x(), rect.bottom())
        right_fin = QPointF(rect.right() - rect.width() * 0.14, rect.top() + rect.height() * 0.88)
        right_body = QPointF(rect.right() - rect.width() * 0.38, rect.top() + rect.height() * 0.78)
        right_shoulder = QPointF(rect.right() - rect.width() * 0.34, rect.top() + rect.height() * 0.28)
        body.moveTo(nose)
        body.lineTo(left_shoulder)
        body.lineTo(left_body)
        body.lineTo(left_fin)
        body.lineTo(rect.center())
        body.lineTo(right_fin)
        body.lineTo(right_body)
        body.lineTo(right_shoulder)
        body.closeSubpath()

        body_grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        body_grad.setColorAt(0.0, QColor("#f3f7fb"))
        body_grad.setColorAt(0.48, QColor("#c7d4e3"))
        body_grad.setColorAt(1.0, QColor("#7f95ae"))
        painter.fillPath(body, body_grad)
        painter.setPen(QPen(QColor("#203145"), 1.2))
        painter.drawPath(body)

        visor = QPainterPath()
        visor.addRoundedRect(
            QRectF(rect.left() + rect.width() * 0.32, rect.top() + rect.height() * 0.40, rect.width() * 0.36, rect.height() * 0.18),
            8.0,
            8.0,
        )
        visor_grad = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        visor_grad.setColorAt(0.0, QColor("#23c7ff"))
        visor_grad.setColorAt(1.0, QColor("#0d3656"))
        painter.fillPath(visor, visor_grad)

        exhaust_pen = QPen(QColor(35, 199, 255, 140))
        exhaust_pen.setWidthF(2.4)
        painter.setPen(exhaust_pen)
        painter.drawLine(
            QPointF(rect.center().x(), rect.bottom() - 8.0),
            QPointF(rect.center().x(), rect.bottom() + 20.0),
        )
        painter.drawLine(
            QPointF(rect.center().x() - 10.0, rect.bottom() - 2.0),
            QPointF(rect.center().x() - 2.0, rect.bottom() + 14.0),
        )
        painter.drawLine(
            QPointF(rect.center().x() + 10.0, rect.bottom() - 2.0),
            QPointF(rect.center().x() + 2.0, rect.bottom() + 14.0),
        )
        painter.restore()
