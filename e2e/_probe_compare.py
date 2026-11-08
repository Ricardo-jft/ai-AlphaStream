# -*- coding: utf-8 -*-
"""抓取一次 /api/ai/chat 对比分析的完整输出，用于核对数据是否与接口一致。
用法: python e2e/_probe_compare.py "对比分析这些股票的投资价值：600519 vs 000858"
"""
import json
import sys
import time

import requests

BASE = "http://127.0.0.1:8888"
msg = sys.argv[1] if len(sys.argv) > 1 else "对比分析这些股票的投资价值：600519 vs 000858"

s = requests.Session()
ck = s.get(f"{BASE}/api/csrf_token", timeout=10).json()
token = ck.get("csrf_token", "")

t0 = time.time()
events = []
buf = ""
resp = s.post(
    f"{BASE}/api/ai/chat",
    json={"message": msg},
    headers={"X-CSRFToken": token, "Content-Type": "application/json"},
    stream=True,
    timeout=400,
)

cur_event = None
text_parts = []
tools = []
# 注意：必须用 bytes 迭代后手动 utf-8 解码。
# requests 的 iter_lines(decode_unicode=True) 在响应头无 charset 时按 latin-1 解码，
# 而部分汉字的 UTF-8 字节（如“茅”的 0x85=NEL）会被 splitlines 当成换行切开，
# 导致整帧 JSON 解析失败、文本静默丢失（曾误判为后端丢字）。
for raw in resp.iter_lines(decode_unicode=False):
    if raw is None:
        continue
    line = raw.decode("utf-8", errors="replace").strip("\r")
    if line.startswith("event:"):
        cur_event = line[6:].strip()
        continue
    if line.startswith("data:"):
        try:
            data = json.loads(line[5:].strip())
        except Exception:
            continue
        if cur_event == "token":
            text_parts.append(data.get("content") or "")
        elif cur_event == "tool_call":
            tools.append(data)
        elif cur_event == "status" or cur_event == "progress":
            events.append(f"[{time.time()-t0:6.1f}s] {cur_event}: {json.dumps(data, ensure_ascii=False)[:160]}")
        elif cur_event in ("done", "error"):
            events.append(f"[{time.time()-t0:6.1f}s] {cur_event}: {json.dumps(data, ensure_ascii=False)[:200]}")
            if cur_event == "done":
                break

text = "".join(text_parts)
print("=" * 30, "耗时", f"{time.time()-t0:.1f}s", "=" * 30)
print("--- 事件 ---")
for e in events:
    print(e)
print(f"--- 工具调用 {len(tools)} 次 ---")
for t in tools:
    print(json.dumps(t, ensure_ascii=False)[:200])
print("--- 正文长度", len(text), "---")
print(text)

with open("e2e/_compare_output.txt", "w", encoding="utf-8") as f:
    f.write(text)
