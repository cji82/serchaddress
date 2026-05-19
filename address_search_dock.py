# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QStackedWidget,
    QProgressBar,
    QToolButton,
    QDockWidget,
    QSplitter,
)
from qgis.PyQt.QtCore import QSize

from .plugin_settings import PluginSettings
from .settings_dialog import SettingsDialog
from .gateway import build_kakao_keyword_url
from .kakao_client import meta_max_page
from .search_worker import SearchWorker
from .map_flash_marker import MapFlashMarker
from .result_widgets import ResultListCard, ResultDetailPanel
from .qt_compat import (
    qt_user_role,
    dialog_exec,
    dialog_accepted,
    size_policy_fixed_fixed,
    qt_right_dock_area,
    qt_all_dock_widget_areas,
    qt_horizontal_orientation,
    qt_align_center,
    transform_wgs84_to_map_point,
    qgis_log_warning,
)

LOG_TAG = "주소검색"
MAX_PAGE = 45


class AddressSearchDockWidget(QWidget):
    """Dock panel: 검색, 카드 목록, 상세 패널, 페이징."""

    def __init__(self, iface, plugin, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.plugin = plugin
        plugin_dir = getattr(plugin, "plugin_dir", "") or ""
        self.settings = PluginSettings(plugin_dir)
        self._search_in_flight = False
        self._request_seq = 0
        self._active_request_id = 0
        self._worker = None
        self._flash = MapFlashMarker(iface.mapCanvas(), plugin_dir)
        self._current_query = ""
        self._current_page = 1
        self._last_meta = {}
        self._build_ui()
        self.edit_query.returnPressed.connect(lambda: self._start_search(1))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self.btn_settings = QToolButton()
        self.btn_settings.setText("⚙")
        self.btn_settings.setToolTip("서비스 설정")
        self.btn_settings.setFixedWidth(28)
        self.btn_settings.clicked.connect(self._open_settings)
        row.addWidget(self.btn_settings)

        self.edit_query = QLineEdit()
        self.edit_query.setPlaceholderText("주소·장소 키워드")
        if hasattr(self.edit_query, "setClearButtonEnabled"):
            self.edit_query.setClearButtonEnabled(True)
        row.addWidget(self.edit_query, 1)

        self.search_stack = QStackedWidget()
        self.search_stack.setFixedSize(72, 28)
        self.search_stack.setSizePolicy(size_policy_fixed_fixed())

        self.btn_search = QPushButton("검색")
        self.btn_search.setMinimumWidth(68)
        self.btn_search.clicked.connect(lambda: self._start_search(1))
        self.search_stack.addWidget(self.btn_search)

        self.search_progress = QProgressBar()
        self.search_progress.setRange(0, 0)
        self.search_progress.setTextVisible(False)
        self.search_progress.setFixedSize(68, 22)
        self.search_stack.addWidget(self.search_progress)

        row.addWidget(self.search_stack)
        layout.addLayout(row)

        self.label_gateway_url = QLabel("")
        self.label_gateway_url.setWordWrap(True)
        self.label_gateway_url.setStyleSheet("color: #555; font-size: 11px;")
        self.label_gateway_url.setVisible(False)
        layout.addWidget(self.label_gateway_url)
        self.edit_query.textChanged.connect(self._update_gateway_url_preview)

        splitter = QSplitter()
        splitter.setOrientation(qt_horizontal_orientation())

        list_wrap = QWidget()
        list_layout = QVBoxLayout(list_wrap)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(4)
        list_title = QLabel("검색 결과")
        list_title.setStyleSheet("font-weight: bold;")
        list_layout.addWidget(list_title)
        self.result_list = QListWidget()
        self.result_list.setSpacing(4)
        self.result_list.setUniformItemSizes(False)
        self._configure_list_selection()
        self.result_list.currentItemChanged.connect(self._on_selection_changed)
        self.result_list.itemPressed.connect(self._on_item_pressed)
        self.result_list.itemClicked.connect(self._on_item_clicked)
        self.result_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        list_layout.addWidget(self.result_list, 1)
        splitter.addWidget(list_wrap)

        self.detail_panel = ResultDetailPanel()
        self.detail_panel.go_to_map_requested = self._go_to_map
        self.detail_panel.setMinimumWidth(200)
        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        page_row = QHBoxLayout()
        self.btn_prev = QPushButton("◀ 이전")
        self.btn_prev.clicked.connect(self._on_prev_page)
        self.label_page = QLabel("페이지 1 / 1")
        self.label_page.setAlignment(qt_align_center())
        self.btn_next = QPushButton("다음 ▶")
        self.btn_next.clicked.connect(self._on_next_page)
        page_row.addWidget(self.btn_prev)
        page_row.addWidget(self.label_page, 1)
        page_row.addWidget(self.btn_next)
        self.pagination_bar = QWidget()
        self.pagination_bar.setLayout(page_row)
        self.pagination_bar.setVisible(False)
        layout.addWidget(self.pagination_bar)

        self.label_status = QLabel("키워드를 입력하고 검색하세요.")
        self.label_status.setWordWrap(True)
        layout.addWidget(self.label_status)

        self.setMinimumWidth(520)
        self._update_gateway_url_preview()

    def _gateway_enabled(self):
        cfg = self.settings.gateway_config()
        return isinstance(cfg, dict) and bool(cfg.get("enabled"))

    def _update_gateway_url_preview(self, page=1):
        if not self._gateway_enabled():
            self.label_gateway_url.setVisible(False)
            return
        q = self.edit_query.text().strip() or "강남역"
        url = build_kakao_keyword_url(
            q,
            page=page,
            size=self._page_size(),
            gateway_cfg=self.settings.gateway_config(),
        )
        self.label_gateway_url.setText("게이트웨이 URL: " + url)
        self.label_gateway_url.setVisible(True)

    def _configure_list_selection(self):
        from qgis.PyQt.QtWidgets import QAbstractItemView
        mode = getattr(QAbstractItemView, "SelectionMode", None)
        if mode is not None:
            self.result_list.setSelectionMode(mode.SingleSelection)
        else:
            self.result_list.setSelectionMode(QAbstractItemView.SingleSelection)
        behavior = getattr(QAbstractItemView, "SelectionBehavior", None)
        if behavior is not None:
            self.result_list.setSelectionBehavior(behavior.SelectRows)
        else:
            self.result_list.setSelectionBehavior(QAbstractItemView.SelectRows)

    def _sync_card_selection_highlight(self):
        current = self.result_list.currentItem()
        for i in range(self.result_list.count()):
            item = self.result_list.item(i)
            card = self.result_list.itemWidget(item)
            if card is not None and hasattr(card, "set_selected"):
                card.set_selected(item is not None and item is current)

    def _open_settings(self):
        dlg = SettingsDialog(
            self,
            plugin_dir=getattr(self.plugin, "plugin_dir", "") or "",
        )
        self.settings.load_into_dialog(dlg)
        if dialog_exec(dlg) == dialog_accepted():
            self.settings.save_from_dialog(dlg)
            self._update_gateway_url_preview()
            self.label_status.setText("설정이 저장되었습니다.")

    def _set_search_loading(self, loading):
        self._search_in_flight = loading
        self.btn_search.setEnabled(not loading)
        self.edit_query.setEnabled(not loading)
        self.btn_settings.setEnabled(not loading)
        self.btn_prev.setEnabled(not loading and self._current_page > 1)
        self.btn_next.setEnabled(not loading and self._can_next_page())
        if loading:
            self.search_stack.setCurrentWidget(self.search_progress)
        else:
            self.search_stack.setCurrentWidget(self.btn_search)

    def _page_size(self):
        return self.settings.page_size()

    def _max_page(self):
        meta = self._last_meta
        if isinstance(meta, dict) and meta.get("is_end"):
            return max(1, self._current_page)
        return meta_max_page(
            meta,
            page_size=self._page_size(),
            api_max_page=MAX_PAGE,
        )

    def _can_next_page(self):
        if not self._last_meta:
            return False
        if self._last_meta.get("is_end", True):
            return False
        return self._current_page < self._max_page()

    def _update_pagination_ui(self, visible=True):
        """검색 후 페이지 바는 항상 표시 (1페이지여도 ◀ ▶ 영역 유지)."""
        self.pagination_bar.setVisible(bool(visible))
        if not visible:
            return

        max_p = self._max_page()
        self.label_page.setText(
            "페이지 {} / {}".format(self._current_page, max_p)
        )
        self.btn_prev.setEnabled(self._current_page > 1 and not self._search_in_flight)
        self.btn_next.setEnabled(self._can_next_page() and not self._search_in_flight)

    def _on_prev_page(self):
        if self._current_page > 1:
            self._start_search(self._current_page - 1)

    def _on_next_page(self):
        if self._can_next_page():
            self._start_search(self._current_page + 1)

    def _start_search(self, page):
        if self._search_in_flight:
            return

        query = self.edit_query.text().strip()
        if not query:
            self.label_status.setText("검색어를 입력하세요.")
            return
        if not self.settings.api_key():
            self.label_status.setText("API 키를 설정하세요.")
            self._open_settings()
            return

        self._current_query = query
        self._current_page = page
        self._update_gateway_url_preview(page=page)

        self._request_seq += 1
        req_id = self._request_seq
        self._active_request_id = req_id
        self._set_search_loading(True)
        self.label_status.setText("검색 중… ({}페이지)".format(page))
        self.result_list.clear()
        self.detail_panel.clear()
        self.pagination_bar.setVisible(True)
        self.label_page.setText("검색 중…")
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

        if self._worker is not None and self._worker.isRunning():
            try:
                self._worker.finished_ok.disconnect()
                self._worker.finished_error.disconnect()
            except (TypeError, RuntimeError):
                pass
            self._worker.wait(3000)

        self._worker = SearchWorker(
            req_id,
            query,
            self.settings.api_key(),
            self.settings.gateway_config(),
            self.iface,
            page=page,
            page_size=self._page_size(),
            parent=self,
        )
        self._worker.finished_ok.connect(self._on_search_ok)
        self._worker.finished_error.connect(self._on_search_error)
        self._worker.start()

    def _populate_list(self, results):
        role = qt_user_role()
        self.result_list.clear()
        for res in results:
            card = ResultListCard(res, self.result_list)
            item = QListWidgetItem(self.result_list)
            item.setSizeHint(QSize(card.sizeHint().width(), 82))
            item.setData(role, res)
            self.result_list.addItem(item)
            self.result_list.setItemWidget(item, card)
            card.bind_list_item(self.result_list, item)
        if results:
            self.result_list.setCurrentRow(0)
        self._sync_card_selection_highlight()

    def _on_search_ok(self, request_id, results, meta):
        if request_id != self._active_request_id:
            return
        self._set_search_loading(False)
        self._last_meta = meta if isinstance(meta, dict) else {}
        self._populate_list(results)
        self._update_pagination_ui()

        if not results:
            self.label_status.setText("검색 결과가 없습니다.")
            self.detail_panel.clear()
            self._update_pagination_ui(visible=True)
        else:
            self.label_status.setText(
                "「{}」 {}페이지 — {}건 표시".format(
                    self._current_query,
                    self._current_page,
                    len(results),
                )
            )

    def _on_search_error(self, request_id, message):
        if request_id != self._active_request_id:
            return
        self._set_search_loading(False)
        self.label_status.setText(message)
        self._update_pagination_ui(visible=bool(self._last_meta))
        qgis_log_warning(message, LOG_TAG)

    def _selected_result(self):
        item = self.result_list.currentItem()
        if item is None:
            return None
        return item.data(qt_user_role())

    def _on_selection_changed(self, current, previous):
        self._sync_card_selection_highlight()
        res = None
        if current is not None:
            res = current.data(qt_user_role())
        if res is not None:
            self.detail_panel.show_result(res)
        else:
            self.detail_panel.clear()

    def _on_item_pressed(self, item):
        self._activate_list_item(item)

    def _on_item_clicked(self, item):
        self._activate_list_item(item)

    def _activate_list_item(self, item):
        if item is None:
            return
        self.result_list.setCurrentItem(item)
        self._sync_card_selection_highlight()
        res = item.data(qt_user_role())
        if res is not None:
            self.detail_panel.show_result(res)

    def _on_item_double_clicked(self, item):
        res = item.data(qt_user_role()) if item else None
        if res is not None:
            self._go_to_map(res)

    def _go_to_map(self, res):
        try:
            x = float(res.x)
            y = float(res.y)
        except (TypeError, ValueError):
            self.label_status.setText("좌표가 올바르지 않습니다.")
            return

        try:
            pt_map = transform_wgs84_to_map_point(self.iface, x, y)
        except Exception as e:
            self.label_status.setText("좌표 변환 실패: {}".format(e))
            qgis_log_warning(str(e), LOG_TAG)
            return

        canvas = self.iface.mapCanvas()
        canvas.setCenter(pt_map)
        canvas.refresh()
        self._flash.show_at(pt_map, self.settings.location_config())
        self.label_status.setText("이동: {}".format(res.list_title()))

    def cleanup(self):
        self._flash.clear()
        if self._worker is not None and self._worker.isRunning():
            try:
                self._worker.finished_ok.disconnect()
                self._worker.finished_error.disconnect()
            except (TypeError, RuntimeError):
                pass
            self._worker.wait(2000)
        self._worker = None


class AddressSearchDock:
    OBJECT_NAME = "SerchAddressDock"

    def __init__(self, iface, plugin):
        self.iface = iface
        self.plugin = plugin
        self.dock = None
        self.panel = None

    def setup(self):
        if self.dock is None:
            self._create()
        self.dock.hide()

    def show(self):
        if self.dock is None:
            self._create()
        self.dock.show()
        self.dock.raise_()
        self.panel.edit_query.setFocus()

    def _create(self):
        self.dock = QDockWidget("주소 검색", self.iface.mainWindow())
        self.dock.setObjectName(self.OBJECT_NAME)
        self.dock.setAllowedAreas(qt_all_dock_widget_areas())
        self.panel = AddressSearchDockWidget(self.iface, self.plugin, self.dock)
        self.dock.setWidget(self.panel)
        self.iface.addDockWidget(qt_right_dock_area(), self.dock)

    def cleanup(self):
        if self.panel is not None:
            self.panel.cleanup()
        if self.dock is not None:
            self.dock.close()
            self.iface.removeDockWidget(self.dock)
        self.dock = None
        self.panel = None

    def open_settings(self):
        if self.panel is None:
            self._create()
        self.panel._open_settings()
