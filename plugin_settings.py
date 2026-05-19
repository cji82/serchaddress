# -*- coding: utf-8 -*-

import os

from qgis.PyQt.QtCore import QSettings

from .kakao_client import normalize_api_key
from .map_flash_marker import (
    MODE_DEFAULT,
    MODE_POINT,
    MODE_ICON,
    copy_user_icon_to_plugin,
)

def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return bool(value)


def _normalize_location_mode(mode):
    m = (mode or MODE_DEFAULT).strip().lower()
    if m in (MODE_DEFAULT, MODE_POINT, MODE_ICON):
        return m
    return MODE_DEFAULT


DEFAULT_PAGE_SIZE = 15
ALLOWED_PAGE_SIZES = (5, 10, 15)


def _normalize_page_size(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    if n in ALLOWED_PAGE_SIZES:
        return n
    return DEFAULT_PAGE_SIZE


class PluginSettings:
    ORG = "serchaddress"
    APP = "settings"

    KEY_API_KEY = "api_key"
    KEY_PAGE_SIZE = "page_size"
    KEY_GATEWAY_ENABLED = "gateway_enabled"
    KEY_GATEWAY_MODE = "gateway_mode"
    KEY_GATEWAY_PREFIX = "gateway_prefix"
    KEY_GATEWAY_TEMPLATE = "gateway_template"
    KEY_GATEWAY_ENCODE = "gateway_encode_target"
    KEY_LOCATION_MODE = "location_mode"
    KEY_LOCATION_ICON_PATH = "location_icon_path"

    def __init__(self, plugin_dir=None):
        self._s = QSettings(self.ORG, self.APP)
        self.plugin_dir = plugin_dir or ""

    def api_key(self):
        return normalize_api_key(self._s.value(self.KEY_API_KEY) or "")

    def set_api_key(self, value):
        self._s.setValue(self.KEY_API_KEY, normalize_api_key(value))

    def page_size(self):
        return _normalize_page_size(self._s.value(self.KEY_PAGE_SIZE, DEFAULT_PAGE_SIZE))

    def set_page_size(self, value):
        self._s.setValue(self.KEY_PAGE_SIZE, _normalize_page_size(value))

    def gateway_config(self):
        return {
            "enabled": _to_bool(self._s.value(self.KEY_GATEWAY_ENABLED, False)),
            "mode": (self._s.value(self.KEY_GATEWAY_MODE) or "none").strip().lower(),
            "prefix": (self._s.value(self.KEY_GATEWAY_PREFIX) or "").strip(),
            "template": (self._s.value(self.KEY_GATEWAY_TEMPLATE) or "").strip(),
            "encode_target": _to_bool(
                self._s.value(self.KEY_GATEWAY_ENCODE, False)
            ),
        }

    def set_gateway_config(self, cfg):
        if not isinstance(cfg, dict):
            return
        self._s.setValue(
            self.KEY_GATEWAY_ENABLED, bool(cfg.get("enabled", False))
        )
        self._s.setValue(
            self.KEY_GATEWAY_MODE, (cfg.get("mode") or "none").strip().lower()
        )
        self._s.setValue(
            self.KEY_GATEWAY_PREFIX, (cfg.get("prefix") or "").strip()
        )
        self._s.setValue(
            self.KEY_GATEWAY_TEMPLATE, (cfg.get("template") or "").strip()
        )
        self._s.setValue(
            self.KEY_GATEWAY_ENCODE, bool(cfg.get("encode_target", False))
        )

    def location_config(self):
        mode = _normalize_location_mode(self._s.value(self.KEY_LOCATION_MODE))
        path = (self._s.value(self.KEY_LOCATION_ICON_PATH) or "").strip()
        if path and not os.path.isfile(path):
            path = ""
        return {"mode": mode, "icon_path": path}

    def set_location_config(self, cfg):
        if not isinstance(cfg, dict):
            return
        mode = _normalize_location_mode(cfg.get("mode"))
        icon_path = (cfg.get("icon_path") or "").strip()
        if mode == MODE_ICON and icon_path and os.path.isfile(icon_path):
            icon_path = copy_user_icon_to_plugin(self.plugin_dir, icon_path)
        self._s.setValue(self.KEY_LOCATION_MODE, mode)
        self._s.setValue(self.KEY_LOCATION_ICON_PATH, icon_path)

    def load_into_dialog(self, dlg):
        dlg.set_values(
            self.api_key(),
            self.gateway_config(),
            self.location_config(),
            self.page_size(),
        )

    def save_from_dialog(self, dlg):
        self.set_api_key(dlg.api_key())
        self.set_gateway_config(dlg.gateway_config())
        self.set_location_config(dlg.location_config())
        self.set_page_size(dlg.page_size())
