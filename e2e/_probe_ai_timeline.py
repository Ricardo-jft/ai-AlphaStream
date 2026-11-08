# Input: 运行中的前端 http://127.0.0.1:3000
# Output: AI 分析全过程时间线（是否真的卡住、几点结束），用于定位"卡住"现象
# Pos: e2e/_probe_ai_timeline.py — 诊断脚本
"""用法：python e2e/_probe_ai_timeline.py"""

import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "http://127.0.0.1:3000"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(2000)
    box = page.locator('textarea[placeholder*="输入股票代码或分析问题"]').first
    box.fill("分析一下600519")
    start = time.time()
    box.press("Enter")

    last_len = 0
    for _ in range(40):  # 最多 ~180s
        time.sleep(5)
        body = page.inner_text("body")
        analyzing = "AI 正在分析中" in body or "AI 正在回复" in body
        print(
            f"[{time.time()-start:5.1f}s] len={len(body):5d} 分析中={analyzing} "
            f"含[已停止]={'[已停止]' in body} 含评分={'评分' in body}"
        )
        if not analyzing and len(body) != last_len:
            print("→ 分析状态已结束")
            break
        last_len = len(body)

    page.screenshot(path="e2e/ai_timeline_final.png", full_page=True)
    print("最终耗时约", round(time.time() - start, 1), "秒")
    browser.close()
