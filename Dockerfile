# 灵析 AI — 根目录多阶段构建
# docker compose build 使用 target: backend | frontend

########## 1. FastAPI 后端（生产端口 8000） ##########
FROM python:3.11-slim AS backend

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN mkdir -p /app/persist

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


########## 2. Vue3 前端构建 ##########
FROM node:20-alpine AS frontend-builder

WORKDIR /app

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/package-lock.json* ./
RUN corepack enable && pnpm install --frozen-lockfile || npm ci || npm install

COPY frontend/ .

# 生产构建：跳过 typecheck 以加快镜像构建（本地仍可用 npm run build）
RUN pnpm exec vite build || npx vite build


########## 3. Nginx 静态托管 + /api 反代 ##########
FROM nginx:alpine AS frontend

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
