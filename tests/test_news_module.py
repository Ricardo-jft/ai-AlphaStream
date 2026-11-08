"""
新闻/舆情板块专项接口测试（GET，免 Key，读取本地新闻缓存 data/news/*.json）。
覆盖：新闻列表结构、条目字段完整性、hash 去重、limit/days 参数边界、
      重要新闻过滤、舆情情绪统计（结构 / 三项合计 / 百分比 / 评分公式 / 幂等）、
      情绪接口参数校验。

运行：
    pytest -q tests/test_news_module.py

说明：新闻列表来自本地缓存文件，若当天缓存为空，依赖数据的用例会 skip 而非 fail。
"""
from datetime import datetime

import pytest

SENTIMENT_KEYS = (
    "total", "bullish", "bearish", "neutral",
    "bullish_pct", "bearish_pct", "neutral_pct", "score",
)


# ---------- 新闻列表 ----------

def test_latest_news_structure(api):
    r = api.get("/api/latest_news", params={"days": 1, "limit": 20}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True or "news" in body
    assert isinstance(body["news"], list)


def test_latest_news_item_fields(api):
    """每条新闻必须具备可渲染的标题 + 可解析的时间 + 唯一 hash。"""
    r = api.get("/api/latest_news", params={"days": 7, "limit": 50}, timeout=30)
    assert r.status_code == 200
    news = r.json()["news"]
    if not news:
        pytest.skip("当前无新闻缓存，跳过字段校验")

    hashes = []
    for item in news:
        assert isinstance(item, dict)
        title = (item.get("title") or "").strip()
        assert title, f"标题为空: {item}"
        # 时间字段：published_at 为统一输出，旧字段 date/time/datetime 兼容
        ts = item.get("published_at") or item.get("datetime") or item.get("date")
        assert ts, f"缺少时间字段: {title}"
        assert isinstance(ts, str)
        h = item.get("hash")
        if h:
            hashes.append(h)

    # 同一批返回内不允许重复（去重是 get_latest_news 的核心职责）
    assert len(hashes) == len(set(hashes)), "返回结果存在重复 hash，去重失效"
    # 来源字段用于前端展示
    assert any(item.get("source") for item in news), "所有新闻均无 source 字段"


def test_latest_news_limit_honored(api):
    """limit 必须真正截断，且返回值不超过 limit。"""
    small = api.get("/api/latest_news", params={"days": 7, "limit": 5}, timeout=30)
    assert small.status_code == 200
    assert len(small.json()["news"]) <= 5

    big = api.get("/api/latest_news", params={"days": 7, "limit": 50}, timeout=30)
    assert big.status_code == 200
    assert len(big.json()["news"]) <= 50
    # 若缓存总量足够，放宽 limit 必须拿到不少于收紧 limit 的条数
    if len(big.json()["news"]) > 5:
        assert len(big.json()["news"]) > len(small.json()["news"]) or len(small.json()["news"]) == 5


@pytest.mark.parametrize("query", [
    {"limit": 0}, {"limit": -1}, {"limit": 1000}, {"limit": "abc"},
    {"days": 0}, {"days": 31}, {"days": "abc"},
])
def test_latest_news_param_validation(api, query):
    r = api.get("/api/latest_news", params=query, timeout=30)
    assert r.status_code == 400, f"{query} 应被拒绝，实际 {r.status_code}"
    body = r.json()
    assert body.get("success") is False
    assert body.get("error_code") == "INVALID_INPUT"


def test_latest_news_important_filter(api):
    """important=1 只允许返回命中关键词的新闻。"""
    keywords = ("重要", "利好", "重磅", "突发", "关注")
    r = api.get("/api/latest_news", params={"days": 7, "limit": 50, "important": 1}, timeout=30)
    assert r.status_code == 200
    news = r.json()["news"]
    for item in news:
        content = (item.get("content") or "") + (item.get("title") or "")
        assert any(k in content for k in keywords), f"重要新闻过滤失效: {item.get('title')}"
    # 过滤结果必须是全集的子集
    full = api.get("/api/latest_news", params={"days": 7, "limit": 50}, timeout=30).json()["news"]
    assert len(news) <= len(full)


# ---------- 舆情情绪 ----------

def test_news_sentiment_structure(api):
    r = api.get("/api/news_sentiment", params={"days": 1}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    for k in SENTIMENT_KEYS:
        assert k in body, f"缺少字段 {k}"
    for k in ("total", "bullish", "bearish", "neutral"):
        assert isinstance(body[k], int) and body[k] >= 0
    assert isinstance(body["score"], (int, float))


def test_news_sentiment_counts_sum(api):
    """三项计数之和必须等于 total，否则分布图会漏数。"""
    body = api.get("/api/news_sentiment", params={"days": 1}, timeout=30).json()
    if body["total"] == 0:
        pytest.skip("当前无新闻，无法校验分布")
    assert body["bullish"] + body["bearish"] + body["neutral"] == body["total"]


def test_news_sentiment_pct_sum(api):
    """三项百分比之和应为 100（允许四舍五入 ±1）。"""
    body = api.get("/api/news_sentiment", params={"days": 1}, timeout=30).json()
    if body["total"] == 0:
        pytest.skip("当前无新闻，无法校验百分比")
    total_pct = body["bullish_pct"] + body["bearish_pct"] + body["neutral_pct"]
    assert 99 <= total_pct <= 101, f"百分比合计 {total_pct} 异常: {body}"
    for k in ("bullish_pct", "bearish_pct", "neutral_pct"):
        assert 0 <= body[k] <= 100


def test_news_sentiment_score_formula(api):
    """score = clamp(5 + (bullish-bearish)/total*5, 1, 10)，保留 1 位小数。"""
    body = api.get("/api/news_sentiment", params={"days": 3}, timeout=30).json()
    if body["total"] == 0:
        pytest.skip("当前无新闻，无法校验评分")
    expected = 5.0 + (body["bullish"] - body["bearish"]) / body["total"] * 5
    expected = max(1.0, min(10.0, expected))
    assert abs(body["score"] - expected) <= 0.05, (
        f"评分与公式不符：实际 {body['score']}，期望 {expected:.2f}，数据 {body}"
    )


def test_news_sentiment_idempotent(api):
    """同一时间窗内连续调用结果必须一致（不应有随机成分）。"""
    a = api.get("/api/news_sentiment", params={"days": 1}, timeout=30).json()
    b = api.get("/api/news_sentiment", params={"days": 1}, timeout=30).json()
    assert a == b, f"连续两次结果不一致: {a} vs {b}"


@pytest.mark.parametrize("query", [{"days": 0}, {"days": 31}, {"days": "abc"}])
def test_news_sentiment_param_validation(api, query):
    r = api.get("/api/news_sentiment", params=query, timeout=30)
    assert r.status_code == 400, f"{query} 应被拒绝，实际 {r.status_code}"
    assert r.json().get("error_code") == "INVALID_INPUT"
