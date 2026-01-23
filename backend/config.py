"""
配置模块：环境变量、日志配置
"""
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==================== 环境变量配置 ====================

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("请设置环境变量 OPENAI_API_KEY")

# DeepSeek 配置（可选）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# VikingDB 配置
VIKINGDB_AK = os.getenv("VIKINGDB_AK")
VIKINGDB_SK = os.getenv("VIKINGDB_SK")
if not VIKINGDB_AK or not VIKINGDB_SK:
    raise ValueError("请设置环境变量 VIKINGDB_AK 和 VIKINGDB_SK")

VIKINGDB_PROJECT = os.getenv("VIKINGDB_PROJECT", "default")
VIKINGDB_PROFILE_TYPE = os.getenv("VIKINGDB_PROFILE_TYPE", "profile_v1")

# VikingDB 多 Collection 配置
COLLECTION_ENV_BY_KEY = {
    "user": "VIKINGDB_COLLECTION_USER",
    "dog": "VIKINGDB_COLLECTION_DOG",
    "relationship": "VIKINGDB_COLLECTION_RELATIONSHIP",
    "conversation": "VIKINGDB_COLLECTION_CONVERSATION",
    "default": "VIKINGDB_COLLECTION",
}

COLLECTION_DEFAULT_NAME_BY_KEY = {
    "user": "user",
    "dog": "dog",
    "relationship": "relationship",
    "conversation": "conversation",
    "default": "dogbot",
}

# ==================== 日志配置 ====================

def setup_logging():
    """
    配置日志系统
    - 按日期创建日志文件
    - 同时输出到文件和控制台
    - 使用统一的日志格式
    """
    # 创建 logs 目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 日志文件名（按日期）
    log_filename = os.path.join(log_dir, f"query_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 配置日志格式
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    return logging.getLogger(__name__)

# 初始化日志
logger = setup_logging()
