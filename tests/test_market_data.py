"""
行情/市场数据模块接口测试（GET，免 Key，需联网调用 akshare）。
默认跳过；设置 RUN_NETWORK_TESTS=1 开启。
覆盖：大盘指数、涨停板、指数成分股、最新资讯、舆情情绪。

运行（需联网）：
    RUN_NETWORK_TESTS=1 pytest -q tests/test_market_data.py
PowerShell:
    $env:RUN_NETWORK_TESTS=1; pytest -q tests/test_market_data.py
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NETWORK_TESTS", "0") != "1",
    reason="需联网调用 akshare，设置 RUN_NETWORK_TESTS=1 开启",
)


def test_market_indices(api):
    r = api.get("/api/market_indices", timeout=30)
    assert r.status_code == 200
    body = r.json()
    for k in ("indices", "meta", "source", "timestamp"):
        assert k in body
    assert isinstance(body["indices"], list)
    if body["indices"]:                     # 有数据时校验单条结构
        assert isinstance(body["indices"][0], dict)


def test_board_stocks(api):
    r = api.get("/api/board_stocks", timeout=30)
    assert r.status_code == 200
    body = r.json()
    for k in ("count", "stock_list"):
        assert k in body
    assert isinstance(body["stock_list"], list)
    assert isinstance(body["count"], int)


def test_index_stocks(api):
    r = api.get("/api/index_stocks", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "stock_list" in body
    assert isinstance(body["stock_list"], list)


def test_latest_news(api):
    r = api.get("/api/latest_news", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "news" in body
    assert isinstance(body["news"], list)
    assert "success" in body


def test_news_sentiment(api):
    r = api.get("/api/news_sentiment", timeout=30)
    assert r.status_code == 200
    body = r.json()
    for k in ("bullish", "bearish", "neutral",
              "bullish_pct", "bearish_pct", "neutral_pct", "score", "total"):
        assert k in body
    assert isinstance(body["total"], int)
