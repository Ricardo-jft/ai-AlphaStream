"""
系统/健康模块接口测试（免外网，无需 LLM Key，适合作为基础断言/冒烟扩展）。
覆盖：深度健康检查、适配器状态、活跃任务、运行指标、OpenAPI 规范。

运行（无需联网，始终执行）：
    pytest -q tests/test_system.py
"""
import pytest


def test_health_deep_structure(api):
    r = api.get("/api/health/deep", timeout=10)
    assert r.status_code == 200
    body = r.json()
    for k in ("status", "uptime_s", "version", "checks", "elapsed_ms"):
        assert k in body, f"缺少字段 {k}"
    assert isinstance(body["checks"], dict)
    assert isinstance(body["uptime_s"], (int, float))


def test_adapters_status_structure(api):
    # 该接口内部会逐个探测数据源(akshare/baostock/wind)连通性，响应较慢
    r = api.get("/api/adapters/status", timeout=60)
    assert r.status_code == 200
    body = r.json()
    for k in ("status", "total", "healthy", "unhealthy", "adapters"):
        assert k in body
    assert isinstance(body["total"], int)
    # adapters 是 {适配器名: {latency_ms, msg, ok}} 的字典
    assert isinstance(body["adapters"], dict)
    if body["adapters"]:
        first = next(iter(body["adapters"].values()))
        assert "ok" in first


def test_active_tasks_structure(api):
    r = api.get("/api/active_tasks", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "active_tasks" in body
    assert isinstance(body["active_tasks"], list)


def test_metrics_structure(api):
    r = api.get("/api/metrics", timeout=10)
    assert r.status_code == 200
    body = r.json()
    for k in ("requests_total", "error_rate", "requests_by_status", "top_paths", "uptime_s"):
        assert k in body
    assert isinstance(body["requests_total"], (int, float))
    assert isinstance(body["top_paths"], list)


def test_openapi_structure(api):
    r = api.get("/api/openapi.json", timeout=10)
    assert r.status_code == 200
    body = r.json()
    for k in ("openapi", "info", "paths"):
        assert k in body
    assert isinstance(body["paths"], dict)
    assert len(body["paths"]) > 0
