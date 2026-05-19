# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QThread, pyqtSignal

from .kakao_client import search_keyword, map_center_wgs84, KakaoSearchError


class SearchWorker(QThread):
    finished_ok = pyqtSignal(int, list, dict)
    finished_error = pyqtSignal(int, str)

    def __init__(
        self,
        request_id,
        query,
        api_key,
        gateway_cfg,
        iface,
        page=1,
        page_size=15,
        parent=None,
    ):
        super().__init__(parent)
        self.request_id = request_id
        self.query = query
        self.api_key = api_key
        self.gateway_cfg = gateway_cfg
        self.iface = iface
        self.page = page
        self.page_size = page_size

    def run(self):
        try:
            center = map_center_wgs84(self.iface) if self.iface else None
            results, meta = search_keyword(
                self.query,
                self.api_key,
                self.gateway_cfg,
                center_xy=center,
                page=self.page,
                size=self.page_size,
            )
            self.finished_ok.emit(self.request_id, results, meta)
        except KakaoSearchError as e:
            self.finished_error.emit(self.request_id, str(e))
        except Exception as e:
            self.finished_error.emit(self.request_id, "검색 실패: {}".format(e))
