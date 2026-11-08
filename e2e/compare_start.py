# Input: 运行中的前端 http://127.0.0.1:3000
# Output: 验证「AI 对比」按钮点击后能真正跳转到对话页并自动发起对比分析
# Pos: e2e/compare_start.py — 对比入口（?q= 参数）回归
"""用法：python e2e/compare_start.py"""

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3000"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(f"{BASE}/compare", wait_until="networkidle")
    page.wait_for_timeout(2500)

    btn = page.get_by_role("button", name="启动AI对比分析")
    print("按钮数量:", btn.count(), "| disabled:", btn.first.is_disabled() if btn.count() else "N/A")
    assert btn.count() >= 1, "页面上找不到「启动AI对比分析」按钮"
    assert not btn.first.is_disabled(), "按钮处于禁用态（股票数不足 2）"

    btn.first.click()
    page.wait_for_timeout(8000)

    print("点击后 URL:", page.url)
    body = page.inner_text("body")
    page.screenshot(path="e2e/compare_started.png", full_page=False)
    print("---- 页面文本片段 ----")
    print(body[:900].replace("\n", " | "))
    print("---- 片段结束 ----")
    assert "对比分析" in body, "跳转后对话区没有出现对比提问（参数未被识别）"
    print("PASS 对比提问已发出")
    print("分析中标记:", "AI 正在分析中" in body or "正在分析" in body)
    browser.close()
    print("ALL PASS · 截图 e2e/compare_started.png")
