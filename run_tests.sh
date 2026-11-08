#!/usr/bin/env bash
# alphastream 接口测试一键脚本（在 Git Bash 中运行）
#
# 前置：
#   1. 已 docker compose up -d backend 起好后端（见下方步骤）
#   2. 本机有 Python 3（用于建虚拟环境跑 pytest）
#
# 用法：
#   ./run_tests.sh                       # 跑冒烟测试 + 生成 HTML/JUnit 报告
#   RUN_NETWORK_TESTS=1 ./run_tests.sh   # 额外跑需联网的数据接口
#   ./run_tests.sh tests/test_api_smoke.py   # 只跑某个文件
set -e

cd "$(dirname "$0")"

# 1) 准备 Python 虚拟环境并安装测试依赖
if [ ! -d .venv ]; then
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

pip install -q -U pip
pip install -q pytest pytest-html requests

# 2) 等待后端就绪（默认 http://localhost:8888/health）
BASE_URL="${TEST_BASE_URL:-http://localhost:8888}"
echo "等待后端就绪: $BASE_URL/health"
READY=0
for i in $(seq 1 30); do
  if curl -sf "$BASE_URL/health" >/dev/null 2>&1; then
    echo "后端已就绪 ✓"
    READY=1
    break
  fi
  sleep 2
done
if [ "$READY" -ne 1 ]; then
  echo "⚠️  后端未就绪，请先 'docker compose up -d backend' 并确保 $BASE_URL/health 可访问"
  exit 1
fi

# 3) 运行测试并生成报告
mkdir -p reports
pytest -q \
  --html=reports/report.html --self-contained-html \
  --junitxml=reports/junit.xml \
  "$@"

echo "报告已生成："
echo "  HTML  : reports/report.html"
echo "  JUnit : reports/junit.xml"
