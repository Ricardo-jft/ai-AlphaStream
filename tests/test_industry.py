"""
行业/个股分析模块接口测试（GET，需参数，免 Key，需联网调用 akshare）。
默认跳过；设置 RUN_NETWORK_TESTS=1 开启。
覆盖：行业成分股（需 industry 参数）、个股资料、个股名称。

运行（需联网）：
    RUN_NETWORK_TESTS=1 pytest -q tests/test_industry.py
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NETWORK_TESTS", "0") != "1",
    reason="需联网调用 akshare，设置 RUN_NETWORK_TESTS=1 开启",
)

STOCK_CODE = os.getenv("TEST_STOCK_CODE", "600519")
INDUSTRY = os.getenv("TEST_INDUSTRY", "半导体")


def test_industry_stocks_ok(api):
    r = api.get(f"/api/industry_stocks?industry={INDUSTRY}", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "stock_list" in body
    assert isinstance(body["stock_list"], list)


def test_industry_stocks_missing_param(api):
    # 缺少必填 industry 应返回 400
    r = api.get("/api/industry_stocks", timeout=30)
    assert r.status_code == 400
    body = r.json()
    assert "error" in body or body.get("success") is False


def test_stock_profile(api):
    r = api.get(f"/api/stock_profile?stock_code={STOCK_CODE}", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), (dict, list))


def test_stock_name(api):
    r = api.get(f"/api/stock_name?stock_code={STOCK_CODE}", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), (dict, list))
