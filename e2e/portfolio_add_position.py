# Input: 运行中的前端 http://127.0.0.1:3000（portfolio 页面）+ Playwright
# Output: 校验「同一股票重复添加 = 加仓合并」：股数累加、成本加权平均、列表不出现重复行
# Pos: e2e/portfolio_add_position.py — 持仓加仓语义的端到端回归脚本
"""用法：python e2e/portfolio_add_position.py"""

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3000"


def fill_and_submit(page, code: str, shares: str, cost: str, name: str = "") -> None:
    if not page.locator("#stock-code").count():
        page.get_by_role("button", name="添加持仓", exact=True).click()
    page.fill("#stock-code", code)
    if name:
        page.fill("#stock-name", name)
    page.fill("#stock-shares", shares)
    page.fill("#stock-cost", cost)
    page.get_by_role("button", name="添加", exact=True).click()


def run() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE}/portfolio", wait_until="networkidle")
        # 干净起点：清掉持久化持仓后重载
        page.evaluate("localStorage.removeItem('stockanal-portfolio')")
        page.reload(wait_until="networkidle")

        # 第一次添加：600519 100 股 @1800
        fill_and_submit(page, "600519", "100", "1800")
        page.wait_for_timeout(800)
        first = page.locator("text=100股").first
        assert first.is_visible(), "首次添加后未显示 100股"
        print("PASS 首次添加 → 100股")

        # 第二次添加同一只：600519 100 股 @1900 → 期望合计 200 股，成本 (1800*100+1900*100)/200 = 1850
        fill_and_submit(page, "600519", "100", "1900")
        page.wait_for_timeout(800)

        # 以持久化状态为准（UI 文案只是表象）
        holdings = page.evaluate(
            "JSON.parse(localStorage.getItem('stockanal-portfolio')).state.holdings"
        )
        print("持仓状态:", holdings)
        assert len(holdings) == 1, f"出现重复持仓行：{holdings}"
        assert holdings[0]["shares"] == 200, f"股数未累加：{holdings[0]['shares']}"
        assert abs(holdings[0]["costPrice"] - 1850) < 0.01, f"成本未加权平均：{holdings[0]['costPrice']}"

        assert page.locator("text=200股").count() > 0, "加仓后未累加到 200股"
        assert page.locator("text=100股").count() == 0, "旧股数仍残留"

        # 不应出现两行 600519
        code_links = page.locator('a[href="/stock/600519"]').count()
        assert code_links == 1, f"出现重复持仓行，600519 行数={code_links}"
        print("PASS 重复添加 → 合并为 200股 @1850，仅 1 行")

        # 持久化落地检查（刷新后仍是 200 股）
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(500)
        assert page.locator("text=200股").count() > 0, "刷新后持仓未持久化"
        print("PASS 刷新后仍为 200股（localStorage 持久化正常）")

        # 场景2：页面已带持仓（模拟用户当前状态），再次添加同一只股票
        fill_and_submit(page, "600519", "100", "1700")
        page.wait_for_timeout(800)
        holdings2 = page.evaluate(
            "JSON.parse(localStorage.getItem('stockanal-portfolio')).state.holdings"
        )
        print("已持仓再加仓:", holdings2)
        assert len(holdings2) == 1, f"出现重复行：{holdings2}"
        assert holdings2[0]["shares"] == 300, f"已持仓再加仓未累加：{holdings2[0]['shares']}"
        assert abs(holdings2[0]["costPrice"] - 1800) < 0.01, (
            f"成本未重算（期望 1800）：{holdings2[0]['costPrice']}"
        )
        assert page.locator("text=300股").count() > 0, "UI 未显示 300股"
        print("PASS 已持仓再加仓 → 200+100=300股 @1800")

        page.screenshot(path="e2e/portfolio_after_add.png", full_page=True)
        browser.close()
        print("ALL PASS · 截图 e2e/portfolio_after_add.png")


if __name__ == "__main__":
    run()
