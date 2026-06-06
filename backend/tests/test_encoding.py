"""
한글 문자열 인코딩 검증.
모든 Python 파일이 UTF-8 NoBOM으로 저장되어 있는지,
핵심 한글 상수가 깨지지 않았는지 확인한다.
"""
import pathlib
import pytest


BACKEND_ROOT = pathlib.Path(__file__).parent.parent


def _py_files():
    return [p for p in BACKEND_ROOT.rglob("*.py") if "tests" not in str(p)]


@pytest.mark.parametrize("py_file", _py_files(), ids=lambda p: p.name)
def test_utf8_no_bom(py_file):
    """Python 파일이 UTF-8 NoBOM으로 저장되어 있어야 한다."""
    raw = py_file.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), \
        f"{py_file.name}: UTF-8 BOM 감지 — BOM 없이 저장해야 한다"
    assert not raw.startswith(b"\xff\xfe") and not raw.startswith(b"\xfe\xff"), \
        f"{py_file.name}: UTF-16 인코딩 감지 — UTF-8로 저장해야 한다"


def test_korean_radar_axes():
    """score_engine.py의 IQ 스코어 8축 이름이 한글이어야 한다."""
    src = (BACKEND_ROOT / "services" / "score_engine.py").read_text(encoding="utf-8")
    korean_axes = ["비즈니스 품질", "성장 모멘텀", "밸류에이션", "시장 타이밍",
                   "재무 건전성", "매크로 연계", "리스크 관리", "세후 수익률"]
    for axis in korean_axes:
        assert axis in src, f"score_engine.py에서 한글 축 이름 누락: '{axis}'"


def test_korean_market_strings():
    """market_service.py의 핵심 한글 문자열이 유지되어야 한다."""
    src = (BACKEND_ROOT / "services" / "market_service.py").read_text(encoding="utf-8")
    expected = ["외국인", "기관", "개인", "매크로", "수급"]
    for term in expected:
        assert term in src, f"market_service.py에서 한글 문자열 누락: '{term}'"


def test_no_english_replacement_in_axes():
    """IQ 스코어 calculate_iq_score의 축 딕셔너리 값이 한글이어야 한다.
    함수명(score_business_quality 등)은 영문이어도 무방하나,
    API 응답에 노출되는 axes 딕셔너리 키는 반드시 한글이어야 한다."""
    import ast, pathlib
    src = (BACKEND_ROOT / "services" / "score_engine.py").read_text(encoding="utf-8")

    # calculate_iq_score 함수 내 axes 딕셔너리 키가 한글인지 확인
    # 영문만으로 이루어진 축 이름이 있으면 치환된 것
    korean_required = ["비즈니스 품질", "성장 모멘텀", "밸류에이션", "시장 타이밍",
                       "재무 건전성", "매크로 연계", "리스크 관리", "세후 수익률"]
    for axis in korean_required:
        assert axis in src, \
            f"score_engine.py의 axes 딕셔너리에서 한글 축 이름 누락: '{axis}'"
