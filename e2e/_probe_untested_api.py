"""
未覆盖接口批量冒烟探测（诊断用，不属于回归套件）。
用途：对 tests/ 里尚未断言的后端接口逐个发一次合理请求，输出状态码与耗时，
      用于识别「500 / 超时 / 参数校验缺失」的接口，再决定补哪些正式用例。
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

API = "http://127.0.0.1:8888"

GETS = [
    ("agent_analysis_history", "/api/agent_analysis_history", {}),
    ("agent_pending_approvals", "/api/agent_pending_approvals", {}),
    ("agent_plans", "/api/agent_plans", {}),
    ("conversations", "/api/conversations", {}),
    ("registry_stats", "/api/registry/stats", {}),
    ("mcp_tools", "/api/mcp/tools", {}),
    ("wind_tools", "/api/wind/tools", {}),
    ("wind_quota", "/api/wind/quota", {}),
    ("stock_data", "/api/stock_data", {"stock_code": "600519"}),
    ("stock_name", "/api/stock_name", {"stock_code": "600519"}),
    ("stock_name_search", "/api/stock_name_search", {"keyword": "茅台"}),
    ("stock_quote_batch", "/api/stock_quote_batch", {"stock_codes": "600519,000858"}),
    ("sector_stocks", "/api/sector_stocks", {"sector": "半导体"}),
    ("individual_fund_flow", "/api/individual_fund_flow", {"stock_code": "600519"}),
    ("individual_fund_flow_rank", "/api/individual_fund_flow_rank", {}),
    ("history_analysis", "/api/history_analysis", {"stock_code": "600519"}),
    ("industry_analysis", "/api/industry_analysis", {"industry": "白酒"}),
    ("industry_detail", "/api/industry_detail", {"industry": "白酒"}),
    ("industry_compare", "/api/industry_compare", {"industries": "白酒,银行"}),
    ("index_analysis", "/api/index_analysis", {"index_code": "sh.000001"}),
    ("alt_data", "/api/alt_data/600519", {}),
    ("esg", "/api/esg/600519", {}),
    ("esg_climate", "/api/esg/climate/0000320193", {}),
    ("satellite_search", "/api/satellite/search", {"lat": "31.2", "lon": "121.5"}),
    ("corporate_search", "/api/corporate/search", {"keyword": "茅台"}),
    ("corporate_network", "/api/corporate/600519/network", {}),
    ("jobs_search", "/api/jobs/search", {"keyword": "测试"}),
    ("jobs_company", "/api/jobs/company/600519", {}),
    ("shipping_bdi", "/api/shipping/bdi", {}),
    ("shipping_port", "/api/shipping/port/上海", {}),
    ("market_stream_head", "/api/market_stream", {}),
]


def probe(item):
    name, path, params = item
    t0 = time.time()
    try:
        r = requests.get(API + path, params=params, timeout=30)
        cost = time.time() - t0
        flag = "OK " if r.status_code == 200 else ("ERR" if r.status_code >= 500 else "4xx")
        body = r.text[:80].replace("\n", " ")
        return (name, r.status_code, cost, flag, body)
    except requests.exceptions.Timeout:
        return (name, 0, time.time() - t0, "TO ", "timeout>30s")
    except Exception as e:
        return (name, 0, time.time() - t0, "EXC", f"{type(e).__name__}: {e}"[:80])


def main():
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(probe, GETS))
    print(f"{'接口':26s} {'状态':>5s} {'耗时':>8s}  结果")
    print("-" * 96)
    for name, code, cost, flag, body in sorted(rows, key=lambda x: -x[2]):
        print(f"{name:26s} {code:5d} {cost:7.2f}s  {flag} {body}")
    bad = [r for r in rows if r[1] != 200]
    print(f"\n合计 {len(rows)} 个：200 有 {len(rows) - len(bad)} 个，异常 {len(bad)} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
