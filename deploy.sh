#!/bin/bash
# 灵析 AI 投顾助手 — 阿里云 ECS 一键部署脚本
set -e

echo "=========================================="
echo "  灵析 Lingxi — Docker 一键部署"
echo "=========================================="

if [ ! -f .env ]; then
  echo "复制 .env.example -> .env，请填入 TUSHARE_TOKEN、DEEPSEEK_API_KEY"
  cp .env.example .env
  echo "请编辑 .env 后重新运行本脚本"
  exit 1
fi

if ! command -v docker &> /dev/null; then
  echo "请先安装 Docker: curl -fsSL https://get.docker.com | sh"
  exit 1
fi

docker compose down 2>/dev/null || true
docker compose up --build -d

echo ""
echo "部署完成！"
echo "  前端: http://<你的ECS公网IP>/"
echo "  API:  http://<你的ECS公网IP>/api/health"
echo ""
echo "查看日志: docker compose logs -f"
echo "停止服务: docker compose down"
