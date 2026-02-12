# A2A 相亲 — Zeabur / 通用 Docker 部署
# 构建与运行均在项目根目录，以便 backend + website 同镜像
FROM python:3.11-slim

WORKDIR /app

# 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 代码（backend + website）
COPY backend ./backend
COPY website ./website

# Zeabur 会注入 PORT，默认 8080
ENV PORT=8080
EXPOSE 8080

# 从项目根启动，保证 backend.server 能正确解析 website 路径
CMD uvicorn backend.server:app --host 0.0.0.0 --port ${PORT}
