"""
资金流/板块模块接口测试（GET + POST，免 Key，需联网调用 akshare）。
默认跳过；设置 RUN_NETWORK_TESTS=1 开启。
覆盖：概念资金流、行业资金流、个股资金流（需 stock_code）、
      北向资金历史（POST，需 stock_code）。

说明：/capital_flow 是前端页面（GET 返回 HTML），不是数据 API，故不测。

运行（需联网）：
    RUN_NETWORK_TESTS=1 pytest -q tests/test_capital_flow.py
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NETWORK_TESTS", "0") != "1",
    reason="需联网调用 akshare，设置 RUN_NETWORK_TESTS=1 开启",
)

STOCK_CODE = os.getenv("TEST_STOCK_CODE", "600519")


def test_concept_fund_flow(api):
    r = api.get("/api/concept_fund_flow", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    if body:
        assert isinstance(body[0], dict)


def test_industry_fund_flow(api):
    r = api.get("/api/industry_fund_flow", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    if body:
        assert isinstance(body[0], dict)


def test_individual_fund_flow_ok(api):
    r = api.get(f"/api/individual_fund_flow?stock_code={STOCK_CODE}", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), (dict, list))


def test_individual_fund_flow_missing_param(api):
    # 缺少必填 stock_code 应返回 400 参数校验错误
    r = api.get("/api/individual_fund_flow", timeout=30)
    assert r.status_code == 400
    body = r.json()
    assert body.get("success") is False or "error" in body


def test_north_flow_history_post(api):
    r = api.post("/api/north_flow_history",
                 json={"stock_code": STOCK_CODE, "days": 10}, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), (dict, list))
