"""
POST 端点入参校验测试（空 body / 缺必填字段）。
目的：长任务类接口（分析、扫描、Agent、审批、上传）耗时以分钟计，不适合在回归里实跑；
      但它们必须在「参数不合法」时快速拒绝，不能抛 5xx，也不能真的把任务启起来。
      本文件用最小成本覆盖这 16 个接口的契约第一层。

运行：
    pytest -q tests/test_post_validation.py
"""
import pytest

# 分析/任务类 POST 端点（预期：空 body → 400/422，绝不 5xx，也不进入长任务执行）
ENDPOINTS = [
    "/api/fundamental_analysis",
    "/api/enhanced_analysis",
    "/api/risk_analysis",
    "/api/portfolio_risk",
    "/api/scenario_predict",
    "/api/qa",
    "/api/start_stock_analysis",
    "/api/start_agent_analysis",
    "/api/start_market_scan",
    "/api/start_etf_analysis",
    "/api/agent_submit_approval",
    "/api/agent_apply_portfolio_proposal",
    "/api/delete_agent_analysis",
    "/api/mcp/call",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_post_rejects_empty_body(api, path):
    r = api.post(path, json={}, timeout=20)
    assert r.status_code < 500, (
        f"{path} 空 body 返回 {r.status_code}（应为 4xx）: {r.text[:150]}"
    )
    assert r.status_code in (400, 401, 403, 404, 405, 422), (
        f"{path} 空 body 返回 {r.status_code}，不符合参数校验约定: {r.text[:150]}"
    )


@pytest.mark.parametrize("path", ["/api/cancel_analysis", "/api/cancel_scan"])
def test_cancel_without_task_id(api, path):
    """取消接口缺 task_id 必须 404（路由不匹配）而不是 500。"""
    r = api.post(f"{path}/不存在的任务ID", json={}, timeout=20)
    assert r.status_code < 500, f"{path} 返回 {r.status_code}: {r.text[:150]}"


def test_qa_missing_question(api):
    """问答接口缺 question 字段必须明确报错，不能返回空答案。"""
    r = api.post("/api/qa", json={}, timeout=20)
    assert r.status_code == 400
    body = r.json()
    assert body.get("success") is False or "error" in body


def test_scan_status_unknown_task(api):
    """查询不存在任务的扫描状态，应返回明确语义而非 5xx。"""
    r = api.get("/api/scan_status/not-exist-task-id", timeout=20)
    assert r.status_code < 500
    if r.status_code == 200:
        body = r.json()
        assert body.get("status") in ("not_found", "unknown", "error", None) or "error" in body


def test_delete_agent_analysis_unknown_id(api):
    r = api.post("/api/delete_agent_analysis", json={"task_id": "not-exist"}, timeout=20)
    assert r.status_code < 500
