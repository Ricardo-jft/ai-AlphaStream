"""
宽口径接口冒烟（覆盖此前只有人工探测、无自动化断言的接口）。
覆盖：任务/审批、会话、注册表、MCP、Wind、个股行情与报价、资金流、行业详情、
      航运、企业检索、ESG。

运行：
    RUN_NETWORK_TESTS=1 pytest -q tests/test_api_broad_smoke.py
说明：这些接口依赖外部数据源，返回结构可能随上游变化，故只断言「可达 + 关键字段存在」，
      不校验具体数值；需要数值正确性的接口见 test_market_data / test_capital_flow。
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NETWORK_TESTS", "0") != "1",
    reason="依赖外部数据源，设置 RUN_NETWORK_TESTS=1 开启",
)


# ---------- 任务 / 审批 / 会话（本地状态，不改数据） ----------

def test_agent_analysis_history(api):
    r = api.get("/api/agent_analysis_history", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_agent_pending_approvals(api):
    r = api.get("/api/agent_pending_approvals", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "approvals" in body and "count" in body
    assert isinstance(body["approvals"], list)


def test_agent_plans(api):
    r = api.get("/api/agent_plans", timeout=15)
    assert r.status_code == 200
    assert "count" in r.json()


def test_conversations_list(api):
    r = api.get("/api/conversations", timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert "conversations" in body
    assert isinstance(body["conversations"], list)
    if body["conversations"]:
        item = body["conversations"][0]
        assert "conversation_id" in item


# ---------- 注册表 / MCP / Wind ----------

def test_registry_stats(api):
    r = api.get("/api/registry/stats", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "domain_count" in body and "domains" in body
    assert body["domain_count"] == len(body["domains"])


def test_mcp_tools(api):
    r = api.get("/api/mcp/tools", timeout=15)
    assert r.status_code == 200
    body = r.json()
    # 允许 tools 为列表，或包一层 data
    tools = body.get("tools") or (body.get("data") or {}).get("tools")
    assert tools is not None, f"未返回工具列表: {list(body.keys())}"


def test_wind_tools(api):
    r = api.get("/api/wind/tools", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "success" in body
    assert "data" in body


def test_wind_quota(api):
    r = api.get("/api/wind/quota", timeout=15)
    assert r.status_code == 200
    data = r.json().get("data") or {}
    assert "date" in data
    assert "percentage" in data


# ---------- 行情 / 个股 ----------

def test_stock_data_kline(api):
    r = api.get("/api/stock_data", params={"stock_code": "600519"}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("data"), list)
    if body["data"]:
        row = body["data"][0]
        for k in ("date", "open", "high", "low", "close"):
            assert k in row, f"K线缺字段 {k}"


def test_stock_name(api):
    r = api.get("/api/stock_name", params={"stock_code": "600519"}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body.get("stock_code") == "600519"
    assert body.get("stock_name")


def test_stock_name_search(api):
    """参数名是 q（不是 keyword），返回 {query, results[], count}。"""
    r = api.get("/api/stock_name_search", params={"q": "茅台"}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body.get("query") == "茅台"
    assert isinstance(body.get("results"), list)
    assert body.get("count") == len(body["results"])
    if body["results"]:
        assert body["results"][0].get("stock_code")


def test_stock_quote_batch(api):
    """参数名是 codes（不是 stock_codes），返回 {results[], errors[], source}。"""
    r = api.get("/api/stock_quote_batch", params={"codes": "600519,000858"}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("results"), list)
    assert isinstance(body.get("errors"), list)
    assert body.get("source"), "缺 source 字段，前端无法判断是否降级数据"
    codes = [x.get("code") for x in body["results"]]
    assert "600519" in codes, f"请求两只股票，未返回 600519: {codes}"
    for row in body["results"]:
        assert row.get("latest_price") is not None


@pytest.mark.parametrize("query", [{"codes": ""}, {"codes": "abc"}, {"codes": "999999"}])
def test_stock_quote_batch_invalid(api, query):
    """非法代码不得抛 500，必须返回结构化错误。"""
    r = api.get("/api/stock_quote_batch", params=query, timeout=30)
    assert r.status_code < 500, f"{query} 触发 5xx: {r.status_code} {r.text[:120]}"


# ---------- 资金流 / 行业 ----------

@pytest.mark.xfail(strict=False, reason="东财个股资金流上游偶发断连，接口直接 503（BUG-02）")
def test_individual_fund_flow(api):
    r = api.get("/api/individual_fund_flow", params={"stock_code": "600519"}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body.get("stock_code") == "600519"
    assert isinstance(body.get("data"), list)


@pytest.mark.xfail(strict=False, reason="行业资金流抓取失败时误返回 404，非幂等（BUG-19）")
def test_industry_detail_is_idempotent(api):
    """同一参数连续 5 次调用，状态码必须一致且为 200。

    实测出现 200/404 交替：industry_detail 依赖「即时行业资金流」缓存，
    上游抓取失败时返回 None → 接口回 404「未找到行业」，把上游故障说成业务不存在。
    """
    codes = []
    for _ in range(5):
        r = api.get("/api/industry_detail", params={"industry": "白酒"}, timeout=30)
        codes.append(r.status_code)
    assert all(c == 200 for c in codes), f"状态码不稳定: {codes}"
    assert len(set(codes)) == 1


# ---------- 另类数据 / 企业 / 航运 ----------

def test_corporate_search(api):
    r = api.get("/api/corporate/search", params={"q": "茅台"}, timeout=40)
    assert r.status_code == 200
    assert "success" in r.json()


def test_shipping_bdi(api):
    r = api.get("/api/shipping/bdi", timeout=40)
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "artifact" in body


def test_shipping_port(api):
    r = api.get("/api/shipping/port/上海", timeout=20)
    assert r.status_code == 200
    assert "artifact" in r.json()


def test_esg_score(api):
    r = api.get("/api/esg/600519", timeout=40)
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "artifact" in body
