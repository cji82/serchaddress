# -*- coding: utf-8 -*-

from urllib.parse import quote, urlencode

KAKAO_KEYWORD_HTTPS = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_KEYWORD_HTTP = "http://dapi.kakao.com/v2/local/search/keyword.json"


def uses_purl_gateway(cfg):
    """ProxyGetContent.do?purl= 형식 여부."""
    if not isinstance(cfg, dict) or not cfg.get("enabled"):
        return False
    if (cfg.get("mode") or "none").lower() != "prefix":
        return False
    return "purl=" in (cfg.get("prefix") or "").lower()


def _split_purl_gateway(prefix, api_base, query_string, encode):
    """
    접두사 + purl(경로만, ? 없음) + & + query=...&page=...
    query_string: 'query=...&page=...' (? 없이)
    """
    purl_val = quote(api_base, safe="") if encode else api_base
    if not query_string:
        return prefix + purl_val
    return prefix + purl_val + "&" + query_string


def build_kakao_keyword_url(query, page=1, size=15, gateway_cfg=None, center_xy=None):
    """
    카카오 keyword API 최종 요청 URL.
    purl 게이트웨이: query/page/size만, 지도 중심 x,y,sort 미사용.
    """
    cfg = gateway_cfg if isinstance(gateway_cfg, dict) else {}
    q = (query or "").strip()
    try:
        page_n = max(1, int(page))
    except (TypeError, ValueError):
        page_n = 1
    try:
        size_n = min(max(int(size), 1), 15)
    except (TypeError, ValueError):
        size_n = 15

    params = {"query": q, "page": page_n, "size": size_n}
    if center_xy and not uses_purl_gateway(cfg):
        lon, lat = center_xy
        if lon is not None and lat is not None:
            params["x"] = str(lon)
            params["y"] = str(lat)
            params["sort"] = "accuracy"

    qs = urlencode(params)
    direct = KAKAO_KEYWORD_HTTPS + "?" + qs

    if not cfg.get("enabled"):
        return direct

    mode = (cfg.get("mode") or "none").lower()
    if mode in ("", "none", "off"):
        return direct

    encode = bool(cfg.get("encode_target"))

    if uses_purl_gateway(cfg):
        prefix = (cfg.get("prefix") or "").strip()
        if not prefix:
            return direct
        return _split_purl_gateway(prefix, KAKAO_KEYWORD_HTTP, qs, encode)

    return wrap_url(direct, cfg)


def wrap_url(url, cfg):
    """Apply gateway prefix/template to any HTTP URL."""
    if not url or not isinstance(url, str):
        return url
    if not isinstance(cfg, dict):
        return url
    if not cfg.get("enabled"):
        return url

    mode = (cfg.get("mode") or "none").lower()
    if mode in ("", "none", "off"):
        return url

    encode = bool(cfg.get("encode_target"))
    payload = quote(url, safe="") if encode else url

    if mode == "prefix":
        prefix = (cfg.get("prefix") or "").strip()
        if not prefix:
            return url
        if "purl=" in prefix.lower():
            base, _, qs = url.partition("?")
            if base.startswith("https://dapi.kakao.com/"):
                base = KAKAO_KEYWORD_HTTP
            return _split_purl_gateway(prefix, base, qs, encode)
        return prefix + payload

    if mode == "template":
        tpl = (cfg.get("template") or "").strip()
        if not tpl:
            return url
        if "{url}" in tpl:
            return tpl.replace("{url}", payload)
        if "{target_url}" in tpl:
            return tpl.replace("{target_url}", payload)
        return tpl + payload

    return url
