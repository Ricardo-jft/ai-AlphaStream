# Input: 运行中的前端 http://127.0.0.1:3000
# Output: ① 新闻页每条新闻标题是否为可跳转链接 ② AI 深度分析能否完整返回（不再 30s 断流）
# Pos: e2e/ai_chat_and_news_links.py — AI 卡住 + 新闻无跳转 两项缺陷的端到端回归
"""用法：python e2e/ai_chat_and_news_links.py"""

import time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3000"


def check_news_links(page) -> None:
    page.goto(f"{BASE}/news", wait_until="networkidle")
    page.wait_for_timeout(3000)
    stock_links = page.locator('a[href^="/stock/"]').count()
    cls_links = page.locator('a[href*="cls.cn"]').count()
    total = page.locator("a[href]").count()
    print(f"新闻页链接统计：站内个股 {stock_links} 条 / 财联社搜索 {cls_links} 条 / 全部 a 标签 {total}")
    assert stock_links + cls_links > 0, "新闻标题仍不可点击（没有任何跳转链接）"
    # 抽样打印首条链接，确认 href 形态
    first = page.locator('a[href^="/stock/"], a[href*="cls.cn"]').first
    print("首条链接：", first.get_attribute("href"), "| target =", first.get_attribute("target"))
    print("PASS 新闻标题可跳转")


def check_ai_analysis(page) -> None:
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(2000)
    box = page.locator('textarea[placeholder*="输入股票代码或分析问题"]').first
    box.fill("分析一下600519")
    start = time.time()
    box.press("Enter")

    last_len, stable = 0, 0
    while time.time() - start < 180:
        txt = page.inner_text("body")
        if len(txt) == last_len:
            stable += 1
        else:
            stable, last_len = 0, len(txt)
        # 连续 4 次采样（约 10s）文本不再增长 → 判定输出结束
        if stable >= 4 and time.time() - start > 12:
            break
        time.sleep(2.5)

    elapsed = time.time() - start
    body = page.inner_text("body")
    print(f"AI 分析耗时 {elapsed:.1f}s，页面文本长度 {len(body)}")
    assert elapsed < 150, f"分析耗时过长：{elapsed:.1f}s"
    assert "分析" in body and len(body) > 400, "页面未出现分析内容"
    assert "[已停止]" not in body, "输出被中断（出现 [已停止]）"
    page.screenshot(path="e2e/ai_analysis_result.png", full_page=True)
    print("PASS AI 深度分析完整返回（无 30s 断流）")


def run() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        check_news_links(page)
        check_ai_analysis(page)
        browser.close()
        print("ALL PASS · 截图 e2e/ai_analysis_result.png")


if __name__ == "__main__":
    run()
