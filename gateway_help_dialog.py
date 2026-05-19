# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
)

from .qt_compat import qt_scroll_bar_as_needed, qtext_edit_line_wrap_no_wrap

_DIALOG_W = 660
_DIALOG_H = 480


HELP_TEXT = """\
게이트웨이란?
  사내망·보안망에서 외부 API(카카오 등)를 직접 호출하지 못할 때,
  조직에서 제공하는 프록시 URL을 통해 요청을 우회하는 방식입니다.
  구현 방식은 기관마다 다르므로, 담당자에게 받은 URL 형식에 맞춰 설정하세요.

────────────────────────────────────────
1. 접두사 (prefix)
────────────────────────────────────────
  카카오 API 전체 URL 앞에 고정 문자열을 붙입니다.

  [일반 접두사]
    접두사 + https://dapi.kakao.com/...?query=...&page=...
    예) 접두사: https://proxy.example.com/fetch?target=
        결과: https://proxy.example.com/fetch?target=https://dapi.kakao.com/...

  [purl= 형식 (LH ProxyGetContent 등)]
    접두사에 purl= 이 포함되면 자동으로 운영 서버 형식에 맞춥니다.
    · purl 값에는 API 경로만 (http://dapi.kakao.com/.../keyword.json)
    · query, page, size는 & 로 이어 붙임 (? 는 한 번만)
    · x, y, sort(지도 중심 보정)는 사용하지 않음

    예) 접두사: https://map.../ProxyGetContent.do?purl=
        결과: ...?purl=http://dapi.kakao.com/.../keyword.json&query=강남역&page=1&size=15

────────────────────────────────────────
2. 템플릿 (template)
────────────────────────────────────────
  {url} 또는 {target_url} 자리에 카카오 API 전체 URL이 들어갑니다.

  예) https://proxy.example.com/tile?u={url}
      → https://proxy.example.com/tile?u=https://dapi.kakao.com/...?query=...

  플레이스홀더가 없으면 템플릿 문자열 뒤에 URL 전체를 이어 붙입니다.

────────────────────────────────────────
3. 대상 URL URL-인코딩
────────────────────────────────────────
  카카오 API URL(또는 purl 경로)을 percent-encoding 합니다.
  게이트웨이가 ? & 등을 쿼리로 잘못 나누는 경우에 켜 보세요.

  · purl= 형식: purl 값만 인코딩, query/page/size는 그대로
  · 일반 접두사·템플릿: 대상 URL 전체를 인코딩

  운영 서버가 인코딩 없이 동작하면 끄는 것이 맞습니다.

────────────────────────────────────────
확인 방법
────────────────────────────────────────
  · 아래 「요청 URL 미리보기」로 실제 호출 URL을 확인하세요.
  · 검색 패널에서도 게이트웨이 사용 시 URL이 표시됩니다.
  · 브라우저·Postman에서 되는 URL과 비교해 보세요.

────────────────────────────────────────
API 키 (참고)
────────────────────────────────────────
  설정에 넣은 REST API 키는 플러그인이 Authorization 헤더로
  요청에 실어 보냅니다.
"""


class GatewayHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("게이트웨이 설정 도움말")
        self._build_ui()
        self.setFixedSize(_DIALOG_W, _DIALOG_H)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setLineWrapMode(qtext_edit_line_wrap_no_wrap())
        text.setHorizontalScrollBarPolicy(qt_scroll_bar_as_needed())
        text.setPlainText(HELP_TEXT)
        layout.addWidget(text)
        row = QHBoxLayout()
        row.addStretch()
        btn = QPushButton("닫기")
        btn.clicked.connect(self.accept)
        row.addWidget(btn)
        layout.addLayout(row)
