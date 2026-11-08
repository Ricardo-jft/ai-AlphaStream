"""
alphastream 接口自动化测试 · 公共配置 (conftest)

两种用法：
1) 对「运行中的服务」做接口测试（推荐，最贴近真实）：
   - 先用 Docker 起后端： docker compose up -d backend   （或本地 python run.py）
   - 然后跑测试：         pytest -q
   - 默认打 http://localhost:8888 ，可用环境变量覆盖：
       TEST_BASE_URL=http://localhost:8888 pytest -q

2) 离线模式（需要装好完整依赖，不推荐在 Windows 手装）：
   - 直接用 Flask 测试客户端，无需起服务/Docker：
       pytest -q --offline
   - flask_client 固件会在缺依赖时自动跳过。

数据类接口（akshare 行情）需要联网，默认跳过；开启：
   RUN_NETWORK_TESTS=1 pytest -q
"""
import os

import pytest
import requests

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8888").rstrip("/")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


@pytest.fixture
def api(http, base_url):
    """对运行中的服务发请求的封装。"""

    class APIClient:
        def __init__(self, session, base):
            self.s = session
            self.base = base

        def _url(self, path):
            return f"{self.base}{path}"

        def get(self, path, **kw):
            return self.s.get(self._url(path), **kw)

        def post(self, path, **kw):
            return self.s.post(self._url(path), **kw)

    return APIClient(http, base_url)


@pytest.fixture
def flask_client():
    """离线模式：直接加载 Flask app 用测试客户端发请求（需完整依赖）。"""
    try:
        import sys
        from pathlib import Path

        root = str(Path(__file__).resolve().parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        from app.web.web_server import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"无法加载 Flask app（可能缺依赖）: {e}")
