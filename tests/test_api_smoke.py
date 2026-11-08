"""
冒烟测试：不依赖 LLM Key、也不强依赖外网的接口。
覆盖 CSRF token 与 Swagger 文档页，验证服务基本可用。
"""
import pytest


@pytest.mark.parametrize("path", [
    "/api/csrf_token",
    "/api/docs",
])
def test_smoke_get_200(api, path):
    r = api.get(path, timeout=10)
    assert r.status_code == 200


def test_csrf_token_is_json(api):
    r = api.get("/api/csrf_token", timeout=10)
    assert r.status_code == 200
    body = r.json()
    # token 可能放在 body 或 Set-Cookie 中，二选一即可
    has_token = ("token" in body) or ("csrf_token" in body)
    assert has_token or r.cookies, "CSRF 接口应返回 token 或 Set-Cookie"
