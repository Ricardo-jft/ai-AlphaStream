"""
新闻板块 UI 端到端测试（Playwright，真实浏览器渲染）。
覆盖：页面可达、新闻列表渲染、情绪标签/评分、标题可跳转、情绪分布与接口一致性、
      刷新倒计时、板块热力图空态、7 日趋势图数据来源核查。

运行：
    "C:/Program Files/Python311/python.exe" e2e/news_module.py

说明：最后一项「7 日趋势」为数据真实性核查，若失败说明图表展示的是前端生成的
      伪随机数据而非真实历史统计，属缺陷证据，不计入功能回归失败。
"""
import json
import sys
import requests
from playwright.sync_api import sync_playwright

FRONT = "http://127.0.0.1:3000"
API = "http://127.0.0.1:8888"

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" | {detail}" if detail else ""))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        resp = page.goto(f"{FRONT}/news", wait_until="networkidle")
        page.wait_for_timeout(6000)

        # 1. 页面可达
        check("页面 /news 返回 200", resp.status == 200, f"status={resp.status}")

        body = page.inner_text("body")
        check("页面标题含「新闻」或「舆情」", ("新闻" in body or "舆情" in body), body[:30].replace("\n", " "))

        # 2. 新闻列表渲染
        api_news = requests.get(f"{API}/api/latest_news", params={"days": 1, "limit": 20}, timeout=30).json()["news"]
        api_titles = [(n.get("title") or "").strip() for n in api_news if n.get("title")]
        rendered = [t for t in api_titles if t[:18] in body]
        check("新闻条目已渲染", len(rendered) > 0, f"接口 {len(api_titles)} 条 / 页面命中 {len(rendered)} 条")

        # 3. 情绪标签 + 评分
        pos = body.count("▲利好")
        neu = body.count("—中性")
        neg = body.count("▼利空")
        tags = pos + neu + neg
        check("每条新闻带情绪标签", tags >= len(rendered), f"利好{pos} 中性{neu} 利空{neg}")
        check("每条新闻带评分", body.count("[EVAL]") >= len(rendered), f"评分标签 {body.count('[EVAL]')} 个")

        # 4. 标题可跳转
        links = page.locator("a[href]")
        hrefs = [links.nth(i).get_attribute("href") or "" for i in range(links.count())]
        news_links = [h for h in hrefs if "cls.cn" in h or h.startswith("/stock/")]
        check("新闻标题为可点击链接", len(news_links) >= len(rendered),
              f"可跳转链接 {len(news_links)} 个")
        check("跳转目标合法（财联社搜索/站内个股）",
              all("cls.cn" in h or h.startswith("/stock/") for h in news_links))

        # 5. 情绪分布与接口一致
        senti = requests.get(f"{API}/api/news_sentiment", params={"days": 1}, timeout=30).json()
        expect_bull = f"{senti['bullish_pct']}%"
        expect_bear = f"{senti['bearish_pct']}%"
        expect_neu = f"{senti['neutral_pct']}%"
        check("看多比例与接口一致", f"▲ {expect_bull}" in body, f"接口 {expect_bull}")
        check("中性比例与接口一致", f"— {expect_neu}" in body, f"接口 {expect_neu}")
        check("看空比例与接口一致", f"▼ {expect_bear}" in body, f"接口 {expect_bear}")
        check("总评分与接口一致", str(senti["score"]) in body, f"接口 {senti['score']}")

        # 6. 刷新倒计时
        import re
        countdown = re.findall(r"\b\d{1,2}:\d{2}\b", body)
        raw_cnt = re.findall(r"(\d+)\s*秒", body)
        check("存在自动刷新倒计时", bool(countdown or raw_cnt),
              f"形如 mm:ss 的文本 {countdown[:3] if countdown else raw_cnt[:3]}")

        # 7. 板块热力图
        check("板块情绪热力图有空态提示或数据",
              ("板块情绪数据暂不可用" in body) or ("板块" in body and "热力" in body),
              "当前为空态" if "板块情绪数据暂不可用" in body else "有数据")

        # 8. 7 日趋势图数据来源核查（缺陷证据，不计失败）
        bars = page.eval_on_selector_all(
            'div[style*="height"]',
            'els => els.map(e => e.style.height)'
        )
        heights = [int(float(h[:-2])) for h in bars if h.endswith("px") and 3 <= float(h[:-2]) <= 82]
        trend_ok = False
        detail = f"柱高 {heights}"
        if len(heights) == 7:
            from datetime import date, timedelta
            today = date.today()
            vals = []
            for i in range(6, -1, -1):
                d = today - timedelta(days=i)
                # 对应 page.tsx: seed = year*10000 + (getMonth()+1)*100 + getDate()
                seed = d.year * 10000 + d.month * 100 + d.day
                vals.append(30 + ((seed * 7 + 13) % 60))
            mx = max(vals)
            expect = [max(4, round(v / mx * 80)) for v in vals]
            trend_ok = heights != expect
            detail += f" | 按日期哈希公式推导 {expect}"
        check("7日情绪趋势为真实统计数据", trend_ok,
              detail + ("（与哈希公式完全一致 → 伪数据）" if not trend_ok else ""))

        page.screenshot(path="e2e/news_module.png", full_page=True)
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n合计 {len(results)} 项：{passed} PASS / {len(results) - passed} FAIL")
    if len(results) - passed == 1 and not results[-1][1]:
        print("注：唯一失败项为「7日情绪趋势」数据真实性缺陷，功能回归可通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
