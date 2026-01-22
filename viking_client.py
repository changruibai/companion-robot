"""
VikingDB 客户端管理模块
负责初始化和管理多个 Collection 的连接
"""
import os
from fastapi import HTTPException
from vikingdb import IAM
from vikingdb.memory import VikingMem
from vikingdb.memory.exceptions import VikingMemException
from config import (
    VIKINGDB_AK, VIKINGDB_SK, VIKINGDB_PROJECT,
    COLLECTION_ENV_BY_KEY, COLLECTION_DEFAULT_NAME_BY_KEY,
    logger
)

# ==================== 全局变量 ====================

# VikingDB 客户端实例（单例）
_viking_client = None

# Collection 缓存（按 key 存储）
_collections_by_key = {}


# ==================== 客户端初始化 ====================

def init_viking_client():
    """
    初始化 VikingDB 客户端
    使用单例模式，避免重复初始化
    """
    global _viking_client
    
    if _viking_client is not None:
        return _viking_client
    
    try:
        # 创建认证对象
        auth = IAM(ak=VIKINGDB_AK, sk=VIKINGDB_SK)
        
        # 创建 VikingMem 客户端
        _viking_client = VikingMem(
            host="api-knowledgebase.mlp.cn-beijing.volces.com",
            region="cn-beijing",
            auth=auth,
            scheme="http",
        )
        
        logger.info("VikingDB 客户端初始化成功")
        return _viking_client
    except Exception as e:
        logger.error(f"VikingDB 客户端初始化失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"VikingDB 客户端初始化失败: {str(e)}"
        )


# ==================== Collection 管理 ====================

def get_collection_by_key(collection_key: str = "default"):
    """
    按 key 获取或初始化集合（带缓存）
    
    Args:
        collection_key: 集合标识（user/dog/relationship/conversation/default）
    
    Returns:
        Collection 对象
    
    Raises:
        HTTPException: 当 collection_key 无效或获取失败时
    """
    global _viking_client, _collections_by_key
    
    # 参数校验和规范化
    if not collection_key:
        collection_key = "default"
    
    if collection_key not in COLLECTION_ENV_BY_KEY:
        logger.error(f"未知的 collection_key: {collection_key}")
        raise HTTPException(
            status_code=400,
            detail=f"未知 collection_key: {collection_key}"
        )
    
    # 如果已缓存，直接返回
    if collection_key in _collections_by_key:
        return _collections_by_key[collection_key]
    
    # 初始化客户端（如果尚未初始化）
    if _viking_client is None:
        _viking_client = init_viking_client()
    
    # 获取集合名称
    env_name = COLLECTION_ENV_BY_KEY[collection_key]
    collection_name = os.getenv(env_name, COLLECTION_DEFAULT_NAME_BY_KEY[collection_key])
    
    try:
        # 获取集合
        coll = _viking_client.get_collection(
            collection_name=collection_name,
            project_name=VIKINGDB_PROJECT,
        )
        
        # 缓存集合
        _collections_by_key[collection_key] = coll
        
        logger.info(
            f"已初始化 collection: key={collection_key}, "
            f"name={collection_name}, project={VIKINGDB_PROJECT}"
        )
        return coll
    except VikingMemException as e:
        logger.error(
            f"无法获取集合({collection_key}/{collection_name}): {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"无法获取集合({collection_key}/{collection_name}): {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取集合时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取集合失败: {str(e)}"
        )


def get_collection():
    """
    兼容旧代码：返回 default 集合
    """
    return get_collection_by_key("default")
