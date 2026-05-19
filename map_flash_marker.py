# -*- coding: utf-8 -*-

import os
import shutil

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsRubberBand, QgsVertexMarker

from .qt_compat import qgs_wkb_point_geometry, qgs_rubberband_icon_cross

MODE_DEFAULT = "default"
MODE_POINT = "point"
MODE_ICON = "icon"
DEFAULT_MS = 3000


class MapFlashMarker:
    """지도 위치 표시: 기본(플래시) / 포인트 유지 / 사용자 아이콘."""

    def __init__(self, canvas, plugin_dir=None):
        self.canvas = canvas
        self.plugin_dir = plugin_dir or ""
        self._band = None
        self._vertex = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer_clear)

    def show_at(self, map_point, location_cfg=None):
        if map_point is None:
            return

        cfg = location_cfg if isinstance(location_cfg, dict) else {}
        mode = (cfg.get("mode") or MODE_DEFAULT).strip().lower()
        icon_path = (cfg.get("icon_path") or "").strip()

        self.clear()

        if mode == MODE_POINT:
            self._show_vertex_point(map_point)
            return
        if mode == MODE_ICON:
            if icon_path and os.path.isfile(icon_path):
                self._show_vertex_icon(map_point, icon_path)
            else:
                self._show_vertex_point(map_point)
            return

        self._show_flash_cross(map_point, DEFAULT_MS)

    def _show_flash_cross(self, map_point, duration_ms):
        rb = QgsRubberBand(self.canvas, qgs_wkb_point_geometry())
        rb.setColor(QColor(255, 60, 60, 200))
        rb.setWidth(4)
        rb.setIcon(qgs_rubberband_icon_cross())
        rb.addPoint(map_point)
        rb.show()
        self._band = rb
        self._timer.start(int(duration_ms))

    def _show_vertex_point(self, map_point):
        m = QgsVertexMarker(self.canvas)
        m.setCenter(map_point)
        m.setColor(QColor(255, 60, 60))
        m.setIconSize(14)
        m.setPenWidth(2)
        icon_type = self._vertex_icon_cross()
        if icon_type is not None:
            m.setIconType(icon_type)
        self._vertex = m

    def _show_vertex_icon(self, map_point, icon_path):
        m = QgsVertexMarker(self.canvas)
        m.setCenter(map_point)
        m.setIconSize(28)
        m.setPenWidth(0)
        icon_type, source = self._vertex_icon_from_file(icon_path)
        if icon_type is not None:
            m.setIconType(icon_type)
        if source:
            m.setIconSource(source)
        else:
            m.setColor(QColor(255, 60, 60))
            cross = self._vertex_icon_cross()
            if cross is not None:
                m.setIconType(cross)
        self._vertex = m

    def _vertex_icon_cross(self):
        if hasattr(QgsVertexMarker, "ICON_CROSS"):
            return QgsVertexMarker.ICON_CROSS
        icon = getattr(QgsVertexMarker, "IconType", None)
        if icon is not None and hasattr(icon, "ICON_CROSS"):
            return icon.ICON_CROSS
        if hasattr(QgsVertexMarker, "ICON_X"):
            return QgsVertexMarker.ICON_X
        return None

    def _vertex_icon_from_file(self, path):
        low = path.lower()
        if low.endswith(".svg"):
            t = getattr(QgsVertexMarker, "ICON_SVG", None)
            if t is None:
                icon = getattr(QgsVertexMarker, "IconType", None)
                if icon is not None:
                    t = getattr(icon, "ICON_SVG", None)
            if t is not None:
                return t, path
        if low.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            for name in ("ICON_PNG", "ICON_FILE", "ICON_BLOB"):
                t = getattr(QgsVertexMarker, name, None)
                if t is not None:
                    return t, path
            icon = getattr(QgsVertexMarker, "IconType", None)
            if icon is not None:
                t = getattr(icon, "ICON_PNG", None) or getattr(icon, "ICON_BLOB", None)
                if t is not None:
                    return t, path
        return None, path

    def _on_timer_clear(self):
        self._clear_band()

    def _clear_band(self):
        if self._band is None:
            return
        try:
            self._band.reset()
        except TypeError:
            try:
                self._band.reset(True)
            except Exception:
                pass
        except Exception:
            pass
        try:
            self.canvas.scene().removeItem(self._band)
        except Exception:
            pass
        try:
            self._band.setParent(None)
            self._band.deleteLater()
        except Exception:
            pass
        self._band = None

    def _clear_vertex(self):
        if self._vertex is None:
            return
        try:
            self.canvas.scene().removeItem(self._vertex)
        except Exception:
            pass
        try:
            self._vertex.setParent(None)
            self._vertex.deleteLater()
        except Exception:
            pass
        self._vertex = None

    def clear(self):
        self._timer.stop()
        self._clear_band()
        self._clear_vertex()


def copy_user_icon_to_plugin(plugin_dir, source_path):
    """사용자 아이콘을 플러그인 폴더에 복사해 경로 유실 방지."""
    if not source_path or not os.path.isfile(source_path):
        return ""
    if not plugin_dir:
        return source_path
    ext = os.path.splitext(source_path)[1].lower() or ".png"
    dest = os.path.join(plugin_dir, "user_location_icon" + ext)
    try:
        shutil.copy2(source_path, dest)
        return dest
    except OSError:
        return source_path
