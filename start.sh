#!/bin/bash

echo "========================================"
echo "灵析 AI智能投顾助手 - 一键启动脚本"
echo "========================================"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

echo "正在构建并启动服务..."
echo ""

# 构建并启动
docker-compose up --build -d

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "服务启动成功!"
    echo "========================================"
    echo ""
    echo "前端访问: http://localhost"
    echo "后端API: http://localhost:8000"
    echo "API文档: http://localhost:8000/docs"
    echo ""
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
    echo ""
else
    echo ""
    echo "错误: 服务启动失败"
    exit 1
fi
