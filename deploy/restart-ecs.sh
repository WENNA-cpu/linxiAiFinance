#!/bin/bash
# 阿里云 ECS — 重启灵析 + 会议助手 + Nginx
set -e

echo "========== 重启灵析 =========="
cd ~/linxiAiFinance
docker compose restart
sleep 2
docker compose ps
curl -sf http://127.0.0.1:8000/docs >/dev/null && echo "灵析后端 OK" || echo "灵析后端 FAIL"
curl -sf http://127.0.0.1:8080/ >/dev/null && echo "灵析前端 OK" || echo "灵析前端 FAIL"

echo ""
echo "========== 重启会议助手 =========="
cd ~/meeting-assistant
docker compose restart
sleep 2
docker compose ps
curl -sf http://127.0.0.1:8001/health | grep -q ok && echo "会议助手后端 OK" || echo "会议助手后端 FAIL"
curl -sf http://127.0.0.1:8081/meeting/ >/dev/null && echo "会议助手前端 OK" || echo "会议助手前端 FAIL"

echo ""
echo "========== 重启 Nginx =========="
nginx -t
systemctl restart nginx

echo ""
echo "========== 经 Nginx 验证 =========="
curl -sf http://127.0.0.1/ >/dev/null && echo "http://127.0.0.1/ OK"
curl -sf http://127.0.0.1/api/market/sentiment | head -c 80; echo
curl -sf http://127.0.0.1/meeting/ >/dev/null && echo "http://127.0.0.1/meeting/ OK"
curl -sf http://127.0.0.1:8001/health 2>/dev/null || curl -sf http://127.0.0.1/api/meeting/recent | head -c 80; echo

echo ""
echo "完成！浏览器访问："
echo "  灵析:     http://$(curl -s ifconfig.me 2>/dev/null || echo '你的公网IP')/"
echo "  会议助手: http://$(curl -s ifconfig.me 2>/dev/null || echo '你的公网IP')/meeting/"
