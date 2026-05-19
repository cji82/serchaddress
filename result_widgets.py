# -*- coding: utf-8 -*-

from html import escape

from qgis.PyQt.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QCursor

from .kakao_client import SearchResult
from .qt_compat import (
    qframe_styled_panel,
    qt_align_top,
    qt_text_selectable_by_mouse,
    qt_wa_transparent_for_mouse_events,
    qt_focus_policy_no_focus,
)


def _dash(text):
    t = (text or "").strip()
    return t if t else "-"


_CARD_STYLE_NORMAL = (
    "ResultListCard { background: palette(base); "
    "border: 1px solid palette(mid); border-radius: 6px; }"
)
_CARD_STYLE_SELECTED = (
    "ResultListCard { background: palette(highlight); "
    "border: 2px solid palette(highlight); border-radius: 6px; }"
    "ResultListCard QLabel { color: palette(highlighted-text); }"
)


class ResultListCard(QFrame):
    """검색 결과 목록용 카드 위젯."""

    def __init__(self, result: SearchResult, parent=None):
        super().__init__(parent)
        self.result = result
        self._selected = False
        self._list_widget = None
        self._list_item = None
        self.setFrameShape(qframe_styled_panel())
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, "CursorShape") else Qt.PointingHandCursor))
        self.setLineWidth(1)
        self.set_selected(False)
        self._build()

    def set_selected(self, selected):
        self._selected = bool(selected)
        if self._selected:
            self.setLineWidth(2)
            self.setStyleSheet(_CARD_STYLE_SELECTED)
        else:
            self.setLineWidth(1)
            self.setStyleSheet(_CARD_STYLE_NORMAL)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        def row(label, value):
            text = "<b>{}</b> {}".format(label, escape(_dash(value)))
            lb = QLabel(text)
            lb.setWordWrap(True)
            lb.setTextFormat(
                Qt.TextFormat.RichText
                if hasattr(Qt, "TextFormat")
                else Qt.RichText
            )
            layout.addWidget(lb)

        row("건물명 :", self.result.place_name)
        row("도로명 :", self.result.road_address_name)
        row("구주소 :", self.result.address_name)

    def bind_list_item(self, list_widget, item):
        self._list_widget = list_widget
        self._list_item = item
        self._make_labels_click_through()

    def _make_labels_click_through(self):
        """라벨(텍스트) 클릭이 카드로 전달되도록 — 어디를 눌러도 선택됨."""
        transparent = qt_wa_transparent_for_mouse_events()
        no_focus = qt_focus_policy_no_focus()
        for lb in self.findChildren(QLabel):
            lb.setAttribute(transparent, True)
            lb.setFocusPolicy(no_focus)

    def _select_this_item(self):
        if self._list_widget is None or self._list_item is None:
            return
        self._list_widget.setCurrentItem(self._list_item)
        self._list_widget.scrollToItem(self._list_item)

    def mousePressEvent(self, event):
        self._select_this_item()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._select_this_item()
        super().mouseReleaseEvent(event)

    def sizeHint(self):
        return QSize(self.parent().width() if self.parent() else 320, 78)


class ResultDetailPanel(QFrame):
    """선택 항목 상세 + 지도 이동."""

    go_to_map_requested = None  # set by parent: pyqtSignal or callback

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self.setFrameShape(qframe_styled_panel())
        self.setStyleSheet(
            "ResultDetailPanel { background: palette(alternate-base); "
            "border: 1px solid palette(mid); border-radius: 6px; }"
        )
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("상세 정보")
        title.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(title)

        self._hint = QLabel("목록에서 항목을 선택하세요.")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet("color: palette(mid);")
        layout.addWidget(self._hint)

        self._detail = QLabel("")
        self._detail.setWordWrap(True)
        self._detail.setAlignment(qt_align_top())
        self._detail.setTextInteractionFlags(qt_text_selectable_by_mouse())
        self._detail.hide()
        layout.addWidget(self._detail, 1)

        self.btn_go = QPushButton("지도로 이동")
        self.btn_go.setEnabled(False)
        self.btn_go.clicked.connect(self._on_go)
        layout.addWidget(self.btn_go)

    def _on_go(self):
        if self._result is not None and callable(self.go_to_map_requested):
            self.go_to_map_requested(self._result)

    def show_result(self, result: SearchResult):
        self._result = result
        self._hint.hide()
        self._detail.show()
        self.btn_go.setEnabled(True)
        lines = [
            "건물명 : {}".format(_dash(result.place_name)),
            "도로명 : {}".format(_dash(result.road_address_name)),
            "구주소 : {}".format(_dash(result.address_name)),
            "",
            "카테고리 : {}".format(_dash(result.category_name)),
            "연락처 : {}".format(_dash(result.phone)),
            "좌표 : {}, {}".format(_dash(result.x), _dash(result.y)),
        ]
        url = (result.raw or {}).get("place_url")
        if url:
            lines.extend(["", "URL : {}".format(url)])
        self._detail.setText("\n".join(lines))

    def clear(self):
        self._result = None
        self._detail.hide()
        self._hint.show()
        self.btn_go.setEnabled(False)
