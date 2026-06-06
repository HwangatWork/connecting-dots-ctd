"""
모든 백엔드 모듈이 오류 없이 import되는지 검증한다.
rootDir=backend 기준으로 실행 — 'from backend.' prefix 없이 import해야 한다.
"""
import importlib
import pytest

MODULES = [
    "config",
    "cache",
    "schemas",
    "data_registry",
    "routers.market",
    "routers.stocks",
    "routers.ticker",
    "routers.status",
    "services.market_service",
    "services.stock_service",
    "services.score_engine",
    "services.technical",
    "providers.yahoo_finance",
    "providers.krx",
    "providers.fear_greed",
    "providers.fred",
    "main",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    """각 모듈이 ImportError 없이 로드되어야 한다."""
    importlib.import_module(module)


def test_no_backend_prefix_in_imports():
    """main.py에 'from backend.' prefix가 없어야 한다 (rootDir=backend)."""
    import pathlib
    main_src = pathlib.Path(__file__).parent.parent.joinpath("main.py").read_text(encoding="utf-8")
    assert "from backend." not in main_src, \
        "main.py에 'from backend.' prefix 발견 — rootDir=backend 환경에서 사용 금지"
