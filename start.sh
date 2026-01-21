#!/bin/bash

# VikingDB 智能记忆助手启动脚本

echo "🚀 启动 VikingDB 智能记忆助手..."

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python"
    exit 1
fi

# 检查 Node.js 环境
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  警告: 未设置 OPENAI_API_KEY 环境变量"
    echo "   请设置: export OPENAI_API_KEY='your-api-key'"
fi

# 启动后端服务器（后台运行）
echo "📦 启动后端服务器..."
python3 server.py &
BACKEND_PID=$!

# 等待后端启动
sleep 2

# 检查后端是否启动成功
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ 后端服务器启动失败"
    exit 1
fi

echo "✅ 后端服务器已启动 (PID: $BACKEND_PID)"

# 启动前端开发服务器
echo "🎨 启动前端开发服务器..."
cd frontend

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    echo "📥 安装前端依赖..."
    npm install
fi

echo "✅ 前端服务器启动中..."
npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo "✨ 服务启动完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 后端 API: http://localhost:8000"
echo "🌐 前端应用: http://localhost:3000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
