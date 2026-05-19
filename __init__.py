# -*- coding: utf-8 -*-

import sys


def _reload_submodules():
    """플러그인 재활성화 시 서브모듈 캐시 제거 (QGIS가 예전 .py를 쓰는 문제 방지)."""
    pkg = __name__
    for name in list(sys.modules):
        if name.startswith(pkg + "."):
            del sys.modules[name]


def classFactory(iface):
    _reload_submodules()
    from .serchaddress import SerchAddressPlugin
    return SerchAddressPlugin(iface)
