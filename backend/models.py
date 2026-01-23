"""
数据模型：所有 Pydantic 请求和响应模型
"""
from pydantic import BaseModel
from typing import Optional, List


# ==================== 查询相关模型 ====================

class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str
    user_id: Optional[str] = "user_001"
    assistant_id: Optional[str] = "assistant_001"
    limit: Optional[int] = 5


class QueryResponse(BaseModel):
    """查询响应模型"""
    answer: str
    memories: List[dict]
    sources: List[str]


# ==================== 画像相关模型 ====================

class ProfileAddRequest(BaseModel):
    """
    添加画像记忆的入参
    - 必填：profile_type、memory_info、user_id
    - 可选：assistant_id、group_id、is_upsert
    """
    profile_type: str = "profile_v1"
    memory_info: dict
    user_id: str
    assistant_id: Optional[str] = "assistant_001"
    group_id: Optional[str] = None
    is_upsert: Optional[bool] = False


class ProfileUpdateRequest(BaseModel):
    """
    更新画像记忆的入参
    - 必填：profile_id
    - 可选：memory_info（不传则只触发记录但不更新内容）
    """
    profile_id: str
    memory_info: Optional[dict] = None


class MultiCollectionProfileAddRequest(ProfileAddRequest):
    """多库画像添加请求（支持指定 collection_key）"""
    collection_key: str = "default"


class MultiCollectionProfileUpdateRequest(ProfileUpdateRequest):
    """多库画像更新请求（支持指定 collection_key）"""
    collection_key: str = "default"


# ==================== 会话相关模型 ====================

class SessionAddRequest(BaseModel):
    """
    写入会话记忆（event_v1）的请求
    用于 conversation 库等
    """
    collection_key: str = "default"
    session_id: str
    user_id: str
    assistant_id: str
    messages: List[dict]
    metadata: Optional[dict] = None


# ==================== 记忆检索模型 ====================

class MemorySearchRequest(BaseModel):
    """通用记忆检索封装"""
    collection_key: str = "default"
    query: str
    filter: Optional[dict] = None
    limit: Optional[int] = 5


# ==================== 调试聊天模型 ====================

class DebugChatRequest(BaseModel):
    """
    多用户 + 多狗 + 多对话 的调试聊天请求
    - user_id: 用户唯一标识（用于 user 库）
    - dog_id: 机器狗唯一标识（用于 dog 库）
    - conversation_id: 对话唯一标识（用于 conversation 库）
    - model: 选择使用的模型 (chatgpt / deepseek)
    """
    query: str
    user_id: str
    dog_id: str
    conversation_id: str
    assistant_id: Optional[str] = "assistant_001"
    limit: Optional[int] = 5
    model: Optional[str] = "chatgpt"  # 默认使用 ChatGPT


class DebugChatResponse(BaseModel):
    """调试聊天响应模型"""
    answer: str
    context: dict
    write_result: Optional[dict] = None
