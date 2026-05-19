# -*- coding: utf-8 -*-

import os

from qgis.PyQt.QtGui import QIcon

from .address_search_dock import AddressSearchDock
from .plugin_settings import PluginSettings
from .qt_compat import qgis_action


ICON_SVG = "serchaddress.svg"
ICON_PNG = "serchaddress.png"


class SerchAddressPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.toolbar = None
        self.dock = None
        self.settings = PluginSettings()

    def tr(self, text):
        return text

    def _icon_path(self):
        """툴바·메뉴: SVG 우선, 없으면 PNG."""
        svg = os.path.join(self.plugin_dir, ICON_SVG)
        if os.path.isfile(svg):
            return svg
        png = os.path.join(self.plugin_dir, ICON_PNG)
        if os.path.isfile(png):
            return png
        return svg

    def _icon(self):
        path = self._icon_path()
        if os.path.isfile(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
        return QIcon()

    def initGui(self):
        icon = self._icon()

        self.toolbar = self.iface.addToolBar(self.tr("주소검색"))
        self.toolbar.setObjectName("SerchAddressToolbar")
        self.toolbar.setWindowTitle(self.tr("주소검색"))

        self.action_search = qgis_action(
            icon,
            self.tr("주소 검색"),
            self.iface.mainWindow(),
        )
        self.action_search.setObjectName("SerchAddressSearch")
        self.action_search.setToolTip(self.tr("Kakao 키워드 주소·장소 검색"))
        self.action_search.setStatusTip(self.tr("주소 검색 패널 열기"))
        self.action_search.triggered.connect(self.run_search_dock)
        self.toolbar.addAction(self.action_search)

        self.action_settings = qgis_action(
            QIcon(),
            self.tr("서비스 설정"),
            self.iface.mainWindow(),
        )
        self.action_settings.setObjectName("SerchAddressSettings")
        self.action_settings.setToolTip(self.tr("Kakao API 키 및 게이트웨이 설정"))
        self.action_settings.triggered.connect(self.run_settings)

        menu = self.tr("&주소검색")
        self.iface.addPluginToMenu(menu, self.action_search)
        self.iface.addPluginToMenu(menu, self.action_settings)

        self.actions.extend([self.action_search, self.action_settings])

        self.dock = AddressSearchDock(self.iface, self)
        self.dock.setup()

    def unload(self):
        if self.dock is not None:
            self.dock.cleanup()
            self.dock = None

        from . import __init__ as _plugin_init
        _plugin_init._reload_submodules()

        menu = self.tr("&주소검색")
        for action in self.actions:
            self.iface.removePluginMenu(menu, action)

        if self.toolbar is not None:
            self.toolbar.deleteLater()
            self.toolbar = None

        self.actions = []

    def run_search_dock(self):
        if self.dock is None:
            self.dock = AddressSearchDock(self.iface, self)
        self.dock.show()

    def run_settings(self):
        if self.dock is None:
            self.dock = AddressSearchDock(self.iface, self)
            self.dock.setup()
        self.dock.show()
        self.dock.open_settings()
