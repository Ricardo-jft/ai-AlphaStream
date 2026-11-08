# 使用Python 3.11基础镜像（依赖包兼容性更好）
FROM python:3.11-slim
# 设置工作目录
WORKDIR /app
# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs /app/data/news /app/data/agent_memory /app/data/agent_reflections /app/data/agent_strategies /app/data/agent_sessions
# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 复制requirements.txt
COPY requirements.txt .

# 安装Python依赖（走 HTTPS 清华源；scipy/sklearn/pandas/numpy/lxml 均有预编译 wheel，无需 apt 编译依赖）
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制应用代码
COPY . .

# 暴露 Flask/Gunicorn 服务端口
EXPOSE 8888

# 使用 Python 标准库执行健康检查，避免依赖镜像中未安装的 curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8888/health', timeout=5).status == 200 else 1)"

# 使用gunicorn启动应用
# gthread + timeout=300：sync worker 下默认 30s 超时会强杀长耗时请求（AI 深度分析、SSE 行情流），
# 表现为前端一直转圈；此处与 docker-compose.yml 的 command 保持一致，避免重建镜像后回退。
CMD ["gunicorn", "--bind", "0.0.0.0:8888", "--workers", "4", "--worker-class", "gthread", "--threads", "8", "--timeout", "300", "--graceful-timeout", "30", "--keep-alive", "75", "app.web.web_server:app"]
