# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QToolButton

from .qt_compat import line_edit_echo_password, line_edit_echo_normal


class PasswordLineEdit(QWidget):
    """비밀번호 입력 + 눈 아이콘으로 표시/숨김 토글."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._edit = QLineEdit()
        self._edit.setEchoMode(line_edit_echo_password())
        layout.addWidget(self._edit, 1)

        self._toggle = QToolButton()
        self._toggle.setCheckable(True)
        self._toggle.setFixedSize(28, 28)
        self._toggle.setToolTip("키 보기")
        self._toggle.setText("\U0001F441")  # 👁
        self._toggle.toggled.connect(self._on_toggle_visibility)
        layout.addWidget(self._toggle)

    def _on_toggle_visibility(self, show_plain):
        if show_plain:
            self._edit.setEchoMode(line_edit_echo_normal())
            self._toggle.setToolTip("키 숨기기")
            self._toggle.setText("\U0001F648")  # 🙈
        else:
            self._edit.setEchoMode(line_edit_echo_password())
            self._toggle.setToolTip("키 보기")
            self._toggle.setText("\U0001F441")

    def text(self):
        return self._edit.text()

    def setText(self, value):
        self._edit.setText(value or "")

    def setPlaceholderText(self, text):
        self._edit.setPlaceholderText(text)

    def setFocus(self):
        self._edit.setFocus()
