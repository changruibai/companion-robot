"""
VikingDB + OpenAI 智能记忆查询服务器
主入口文件：整合所有模块并启动 FastAPI 服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import logger
from routes import setup_routes

# ==================== FastAPI 应用初始化 ====================

app = FastAPI(title="VikingDB 智能记忆助手")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置所有路由
setup_routes(app)

logger.info("VikingDB 智能记忆助手服务已启动")


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
