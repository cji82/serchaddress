# -*- coding: utf-8 -*-

import os

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QPushButton,
    QLabel,
    QRadioButton,
    QButtonGroup,
    QFileDialog,
    QMessageBox,
    QTextEdit,
)

from .gateway import build_kakao_keyword_url
from .gateway_help_dialog import GatewayHelpDialog
from .password_line_edit import PasswordLineEdit
from .qt_compat import dialog_exec
from .map_flash_marker import MODE_DEFAULT, MODE_POINT, MODE_ICON


class SettingsDialog(QDialog):
    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir or ""
        self.setWindowTitle("서비스 설정 (v1.1.11)")
        self.setMinimumWidth(460)
        self._build_ui()
        self._on_gateway_toggled()
        self._on_gateway_mode_changed()
        self._on_location_mode_changed()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        api_group = QGroupBox("Kakao API")
        api_form = QFormLayout(api_group)
        self.api_key_edit = PasswordLineEdit()
        self.api_key_edit.setPlaceholderText(
            "REST API 키 (KakaoAK 접두사 없이 입력 가능)"
        )
        api_form.addRow("API 키:", self.api_key_edit)
        layout.addWidget(api_group)

        search_group = QGroupBox("검색 표시")
        search_form = QFormLayout(search_group)
        self.page_size_combo = QComboBox()
        for n in (5, 10, 15):
            self.page_size_combo.addItem("{}건".format(n), n)
        self.page_size_combo.setToolTip(
            "한 페이지 API 요청 건수. 카카오 keyword API 최대 15건."
        )
        search_form.addRow("페이지당 건수:", self.page_size_combo)
        layout.addWidget(search_group)

        loc_group = QGroupBox("위치 표시")
        loc_layout = QVBoxLayout(loc_group)

        self.loc_btn_group = QButtonGroup(self)

        self.radio_loc_default = QRadioButton("기본 (디폴트)")
        self.radio_loc_default.setToolTip(
            "십자 마커가 약 3초간 표시된 뒤 사라집니다. (현재와 동일)"
        )
        loc_layout.addWidget(self.radio_loc_default)
        loc_layout.addWidget(
            QLabel(
                "  · 검색 결과 이동 시 빨간 십자 플래시 → 3초 후 자동 제거"
            )
        )

        self.radio_loc_point = QRadioButton("포인트 유지")
        self.radio_loc_point.setToolTip("지도에 포인트 마커를 남겨 두고 유지합니다.")
        loc_layout.addWidget(self.radio_loc_point)
        loc_layout.addWidget(
            QLabel("  · 다음 결과를 선택할 때까지 포인트가 지도에 유지")
        )

        self.radio_loc_icon = QRadioButton("사용자 아이콘")
        loc_layout.addWidget(self.radio_loc_icon)
        loc_layout.addWidget(
            QLabel("  · 선택한 이미지(PNG/SVG 등)로 위치를 표시하고 유지")
        )

        self.loc_btn_group.addButton(self.radio_loc_default)
        self.loc_btn_group.addButton(self.radio_loc_point)
        self.loc_btn_group.addButton(self.radio_loc_icon)
        self.radio_loc_default.setChecked(True)
        self.loc_btn_group.buttonClicked.connect(self._on_location_mode_changed)

        icon_row = QHBoxLayout()
        self.icon_path_edit = QLineEdit()
        self.icon_path_edit.setReadOnly(True)
        self.icon_path_edit.setPlaceholderText("이미지 파일을 선택하세요")
        self.btn_pick_icon = QPushButton("이미지 선택…")
        self.btn_pick_icon.clicked.connect(self._pick_icon_file)
        icon_row.addWidget(self.icon_path_edit, 1)
        icon_row.addWidget(self.btn_pick_icon)
        loc_layout.addLayout(icon_row)

        layout.addWidget(loc_group)

        gw_group = QGroupBox("게이트웨이 (선택)")
        gw_layout = QVBoxLayout(gw_group)
        gw_enable_row = QHBoxLayout()
        self.gateway_enabled = QCheckBox("게이트웨이 사용")
        self.gateway_enabled.toggled.connect(self._on_gateway_toggled)
        gw_enable_row.addWidget(self.gateway_enabled)
        self.btn_gateway_help = QPushButton("도움말 보기")
        self.btn_gateway_help.setToolTip("접두사·템플릿·URL 인코딩 설명")
        self.btn_gateway_help.clicked.connect(self._show_gateway_help)
        gw_enable_row.addWidget(self.btn_gateway_help)
        gw_enable_row.addStretch()
        gw_layout.addLayout(gw_enable_row)

        self.gateway_mode = QComboBox()
        self.gateway_mode.addItem("없음", "none")
        self.gateway_mode.addItem("접두사", "prefix")
        self.gateway_mode.addItem("템플릿", "template")
        self.gateway_mode.currentIndexChanged.connect(self._on_gateway_mode_changed)
        gw_layout.addWidget(QLabel("모드:"))
        gw_layout.addWidget(self.gateway_mode)

        self.gateway_prefix = QLineEdit()
        self.gateway_prefix.setPlaceholderText(
            "예: https://map.../ProxyGetContent.do?purl="
        )
        gw_layout.addWidget(QLabel("접두사:"))
        gw_layout.addWidget(self.gateway_prefix)

        self.gateway_template = QLineEdit()
        self.gateway_template.setPlaceholderText(
            "예: https://intranet.example.com/tile?u={url}"
        )
        gw_layout.addWidget(QLabel("템플릿:"))
        gw_layout.addWidget(self.gateway_template)

        self.gateway_encode = QCheckBox("대상 URL URL-인코딩")
        gw_layout.addWidget(self.gateway_encode)

        gw_layout.addWidget(QLabel("요청 URL 미리보기 (예: 강남역, 1페이지):"))
        self.gateway_url_preview = QTextEdit()
        self.gateway_url_preview.setReadOnly(True)
        self.gateway_url_preview.setMaximumHeight(72)
        self.gateway_url_preview.setPlaceholderText("게이트웨이를 켜면 조립된 URL이 표시됩니다.")
        gw_layout.addWidget(self.gateway_url_preview)

        self.gateway_enabled.toggled.connect(self._update_gateway_preview)
        self.gateway_mode.currentIndexChanged.connect(self._update_gateway_preview)
        self.gateway_prefix.textChanged.connect(self._update_gateway_preview)
        self.gateway_template.textChanged.connect(self._update_gateway_preview)
        self.gateway_encode.toggled.connect(self._update_gateway_preview)
        self.page_size_combo.currentIndexChanged.connect(self._update_gateway_preview)

        layout.addWidget(gw_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_save = QPushButton("저장")
        self.btn_cancel = QPushButton("취소")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    def _on_location_mode_changed(self):
        use_icon = self.radio_loc_icon.isChecked()
        self.icon_path_edit.setEnabled(use_icon)
        self.btn_pick_icon.setEnabled(use_icon)

    def _pick_icon_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "위치 표시 아이콘 선택",
            self.plugin_dir or "",
            "이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.svg);;모든 파일 (*.*)",
        )
        if path:
            self.icon_path_edit.setText(path)
            self.radio_loc_icon.setChecked(True)

    def _show_gateway_help(self):
        dlg = GatewayHelpDialog(self)
        dialog_exec(dlg)

    def _on_gateway_toggled(self):
        on = self.gateway_enabled.isChecked()
        self.btn_gateway_help.setEnabled(on)
        self.gateway_mode.setEnabled(on)
        self.gateway_encode.setEnabled(on)
        self._on_gateway_mode_changed()

    def _on_gateway_mode_changed(self):
        if not self.gateway_enabled.isChecked():
            self.gateway_prefix.setEnabled(False)
            self.gateway_template.setEnabled(False)
            self._update_gateway_preview()
            return
        mode = self.gateway_mode.currentData()
        self.gateway_prefix.setEnabled(mode == "prefix")
        self.gateway_template.setEnabled(mode == "template")
        self._update_gateway_preview()

    def _update_gateway_preview(self):
        if not self.gateway_enabled.isChecked():
            self.gateway_url_preview.clear()
            self.gateway_url_preview.setPlaceholderText(
                "게이트웨이를 켜면 조립된 URL이 표시됩니다."
            )
            return
        url = build_kakao_keyword_url(
            "강남역",
            page=1,
            size=self.page_size(),
            gateway_cfg=self.gateway_config(),
        )
        self.gateway_url_preview.setPlainText(url)

    def set_values(self, api_key, gateway_cfg, location_cfg=None, page_size=15):
        self.api_key_edit.setText(api_key or "")

        idx = self.page_size_combo.findData(int(page_size) if page_size else 15)
        self.page_size_combo.setCurrentIndex(idx if idx >= 0 else 2)

        cfg = gateway_cfg if isinstance(gateway_cfg, dict) else {}
        self.gateway_enabled.setChecked(bool(cfg.get("enabled")))
        mode = (cfg.get("mode") or "none").lower()
        idx = self.gateway_mode.findData(mode)
        self.gateway_mode.setCurrentIndex(idx if idx >= 0 else 0)
        self.gateway_prefix.setText(cfg.get("prefix") or "")
        self.gateway_template.setText(cfg.get("template") or "")
        self.gateway_encode.setChecked(bool(cfg.get("encode_target")))
        self._on_gateway_toggled()
        self._update_gateway_preview()

        loc = location_cfg if isinstance(location_cfg, dict) else {}
        loc_mode = (loc.get("mode") or MODE_DEFAULT).lower()
        if loc_mode == MODE_POINT:
            self.radio_loc_point.setChecked(True)
        elif loc_mode == MODE_ICON:
            self.radio_loc_icon.setChecked(True)
        else:
            self.radio_loc_default.setChecked(True)
        self.icon_path_edit.setText(loc.get("icon_path") or "")
        self._on_location_mode_changed()

    def api_key(self):
        return self.api_key_edit.text().strip()

    def page_size(self):
        data = self.page_size_combo.currentData()
        return int(data) if data is not None else 15

    def gateway_config(self):
        return {
            "enabled": self.gateway_enabled.isChecked(),
            "mode": self.gateway_mode.currentData() or "none",
            "prefix": self.gateway_prefix.text().strip(),
            "template": self.gateway_template.text().strip(),
            "encode_target": self.gateway_encode.isChecked(),
        }

    def location_config(self):
        if self.radio_loc_point.isChecked():
            mode = MODE_POINT
        elif self.radio_loc_icon.isChecked():
            mode = MODE_ICON
        else:
            mode = MODE_DEFAULT
        return {
            "mode": mode,
            "icon_path": self.icon_path_edit.text().strip(),
        }

    def accept(self):
        if self.radio_loc_icon.isChecked():
            path = self.icon_path_edit.text().strip()
            if not path or not os.path.isfile(path):
                QMessageBox.warning(
                    self,
                    "위치 표시",
                    "사용자 아이콘 모드에서는 이미지 파일을 선택해야 합니다.",
                )
                return
        super().accept()
