# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import List, Optional, Tuple
import requests

from .gateway import build_kakao_keyword_url
REQUEST_TIMEOUT = 10


@dataclass
class SearchResult:
    place_name: str
    road_address_name: str
    address_name: str
    category_name: str
    phone: str
    x: str
    y: str
    raw: dict

    @classmethod
    def from_document(cls, doc):
        if not isinstance(doc, dict):
            doc = {}
        return cls(
            place_name=doc.get("place_name") or "",
            road_address_name=doc.get("road_address_name") or "",
            address_name=doc.get("address_name") or "",
            category_name=doc.get("category_name") or "",
            phone=doc.get("phone") or "",
            x=str(doc.get("x") or ""),
            y=str(doc.get("y") or ""),
            raw=doc,
        )

    def list_title(self):
        return self.place_name or self.road_address_name or self.address_name or "(이름 없음)"

    def list_subtitle(self):
        parts = []
        if self.road_address_name:
            parts.append(self.road_address_name)
        if self.address_name and self.address_name != self.road_address_name:
            parts.append(self.address_name)
        if self.category_name:
            parts.append(self.category_name)
        if self.phone:
            parts.append(self.phone)
        return " · ".join(parts)


class KakaoSearchError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def normalize_api_key(api_key):
    """REST API 키만 남김 (KakaoAK 접두사·공백 제거)."""
    key = (api_key or "").strip()
    for prefix in ("KakaoAK ", "KAKAOAK ", "kakaoak "):
        if key.startswith(prefix):
            key = key[len(prefix) :].strip()
    return key


def search_keyword(
    query,
    api_key,
    gateway_cfg,
    center_xy=None,
    page=1,
    size=15,
):
    """
    Keyword search. center_xy: optional (lon, lat) in WGS84 for bias.
    Returns (results, meta_dict).
    """
    q = (query or "").strip()
    if not q:
        raise KakaoSearchError("검색어를 입력하세요.")
    key = normalize_api_key(api_key)
    if not key:
        raise KakaoSearchError("API 키가 설정되지 않았습니다.")

    url = build_kakao_keyword_url(
        q,
        page=page,
        size=size,
        gateway_cfg=gateway_cfg or {},
        center_xy=center_xy,
    )

    headers = {"Authorization": "KakaoAK {}".format(key)}
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        raise KakaoSearchError("요청 시간이 초과되었습니다.")
    except requests.exceptions.RequestException as e:
        raise KakaoSearchError("네트워크 오류: {}".format(e))

    if resp.status_code == 401:
        hint = _http_error_hint(resp, gateway_cfg)
        raise KakaoSearchError(
            "API 키가 올바르지 않습니다. REST API 키인지, "
            "로컬 API가 활성화됐는지 확인하세요.{}".format(hint),
            401,
        )
    if resp.status_code == 403:
        hint = _http_error_hint(resp, gateway_cfg)
        raise KakaoSearchError("API 접근이 거부되었습니다.{}".format(hint), 403)
    if resp.status_code == 429:
        raise KakaoSearchError("API 호출 한도를 초과했습니다.", 429)
    if resp.status_code != 200:
        raise KakaoSearchError(
            "API 오류 (HTTP {})".format(resp.status_code), resp.status_code
        )

    try:
        data = resp.json()
    except ValueError:
        raise KakaoSearchError("응답을 해석할 수 없습니다.")

    docs = data.get("documents") or []
    results = [SearchResult.from_document(d) for d in docs]
    meta = data.get("meta") or {}
    return results, meta


def meta_max_page(meta, page_size=15, api_max_page=45):
    """마지막 페이지 = ceil(pageable_count / page_size). 예: 33건·size15 → 3페이지."""
    if not isinstance(meta, dict) or page_size < 1:
        return 1

    pageable = meta.get("pageable_count")
    if pageable is None:
        return 1
    try:
        p = int(pageable)
    except (TypeError, ValueError):
        return 1
    if p <= 0:
        return 1

    pages = (p + page_size - 1) // page_size
    return min(api_max_page, max(1, pages))


def _http_error_hint(resp, gateway_cfg):
    parts = []
    try:
        body = resp.json()
        msg = body.get("msg") or body.get("message")
        if msg:
            parts.append(" ({})".format(msg))
    except ValueError:
        pass
    if isinstance(gateway_cfg, dict) and gateway_cfg.get("enabled"):
        parts.append(" [게이트웨이 사용 중 — URL·프록시 설정 확인]")
    return "".join(parts)


def map_center_wgs84(iface) -> Optional[Tuple[float, float]]:
    """Current map canvas center as (lon, lat) for search bias."""
    try:
        from qgis.core import (
            QgsCoordinateReferenceSystem,
            QgsCoordinateTransform,
            QgsProject,
            QgsPointXY,
        )

        canvas = iface.mapCanvas()
        center = canvas.center()
        dest = canvas.mapSettings().destinationCrs()
        if not dest.isValid():
            return None
        src = dest
        tgt = QgsCoordinateReferenceSystem("EPSG:4326")
        ctx = QgsProject.instance().transformContext()
        tr = QgsCoordinateTransform(src, tgt, ctx)
        pt = tr.transform(QgsPointXY(center))
        return (pt.x(), pt.y())
    except Exception:
        return None
