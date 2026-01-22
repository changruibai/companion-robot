"""
记忆工具模块：记忆搜索、提取、处理等工具函数
"""
import json
import re
import logging
from typing import List, Optional, Dict
from datetime import datetime
from fastapi import HTTPException
from vikingdb.memory.exceptions import VikingMemException
from viking_client import get_collection_by_key
from config import logger

# ==================== 记忆搜索 ====================

def search_viking_memories(
    query: str,
    user_id: str,
    assistant_id: str,
    limit: int = 5,
    collection_key: str = "default",
    extra_filter: Optional[dict] = None
) -> tuple[List[dict], List[str]]:
    """
    搜索 VikingDB 记忆库（可指定 collection_key）
    
    Args:
        query: 查询文本
        user_id: 用户ID
        assistant_id: 助手ID
        limit: 返回结果数量限制
        collection_key: 集合标识
        extra_filter: 额外的过滤条件
    
    Returns:
        (memories, sources) 元组
        - memories: 记忆列表，每个元素包含 content, score, memory_type 等
        - sources: 来源摘要列表
    """
    # 记录查询参数
    query_params = {
        "query": query,
        "user_id": user_id,
        "assistant_id": assistant_id,
        "limit": limit,
        "collection_key": collection_key
    }
    logger.info(f"【记忆搜索】查询参数: {json.dumps(query_params, ensure_ascii=False, indent=2)}")
    
    try:
        # 获取集合
        coll = get_collection_by_key(collection_key)
        
        # 构建过滤条件
        filter_params = {
            "memory_type": ["profile_v1", "event_v1"],
            "user_id": user_id,
            "assistant_id": assistant_id
        }
        if extra_filter and isinstance(extra_filter, dict):
            filter_params.update(extra_filter)
        
        logger.info(f"【记忆搜索】过滤条件: {json.dumps(filter_params, ensure_ascii=False, indent=2)}")
        
        # 执行搜索
        result = coll.search_memory(
            query=query,
            filter=filter_params,
            limit=limit
        )
        
        # 记录原始响应结果
        logger.info(f"【记忆搜索】原始响应: {json.dumps(result, ensure_ascii=False, indent=2, default=str)}")
        
        # 解析结果
        memories, sources = _parse_search_result(result)
        
        logger.info(f"【记忆搜索】解析完成: 找到 {len(memories)} 条记忆")
        return memories, sources
        
    except VikingMemException as e:
        error_msg = f"VikingDB 搜索异常: {str(e)}"
        logger.error(error_msg)
        logger.error(f"错误详情: {json.dumps({'error': str(e), 'type': type(e).__name__}, ensure_ascii=False)}")
        return [], []
    except Exception as e:
        error_msg = f"搜索记忆库失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"错误详情: {json.dumps({'error': str(e), 'type': type(e).__name__}, ensure_ascii=False)}")
        import traceback
        logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
        return [], []


def _parse_search_result(result: dict) -> tuple[List[dict], List[str]]:
    """
    解析搜索结果的内部函数
    
    Args:
        result: VikingDB 返回的原始结果
    
    Returns:
        (memories, sources) 元组
    """
    memories = []
    sources = []
    
    if not result or not isinstance(result, dict) or not result.get('data'):
        logger.info("【记忆搜索】未找到相关记忆数据")
        return memories, sources
    
    result_data = result['data']
    count = result_data.get('count', 0)
    logger.info(f"【记忆搜索】找到 {count} 条记忆记录")
    
    if count <= 0 or 'result_list' not in result_data:
        logger.info("【记忆搜索】结果列表为空")
        return memories, sources
    
    # 处理每条记录
    for idx, item in enumerate(result_data['result_list'], 1):
        logger.info(f"【记忆搜索】处理第 {idx} 条记录")
        
        # 提取记忆内容
        memory_content = _extract_memory_content(item)
        
        if not memory_content:
            logger.warning(f"【记忆搜索】第 {idx} 条记录未找到有效记忆内容")
            continue
        
        # 构建记忆项
        memory_item = _build_memory_item(item, memory_content)
        memories.append(memory_item)
        sources.append(memory_content[:100] + ("..." if len(memory_content) > 100 else ""))
        
        logger.info(
            f"【记忆搜索】提取成功: 内容={memory_content[:200]}..., "
            f"分数={memory_item.get('score')}, 类型={memory_item.get('memory_type')}"
        )
    
    return memories, sources


def _extract_memory_content(item: dict) -> Optional[str]:
    """
    从记忆项中提取内容
    
    根据不同的 memory_type 提取不同的字段：
    - event_v1: 优先使用 summary，其次使用 original_messages
    - profile_v1: 使用 user_profile
    - 其他: 尝试通用字段
    
    Args:
        item: 记忆项字典
    
    Returns:
        提取的内容字符串，如果未找到则返回 None
    """
    memory_type = item.get('memory_type', 'unknown')
    memory_info = item.get('memory_info', {})
    
    memory_content = None
    
    # 根据记忆类型解析不同的字段
    if isinstance(memory_info, dict):
        if memory_type == 'event_v1':
            # 事件类型：优先使用 summary，其次使用 original_messages
            summary = memory_info.get('summary', '')
            original_messages = memory_info.get('original_messages', '')
            
            if summary and summary != 'null' and summary.strip():
                memory_content = summary
            elif original_messages and original_messages != 'null' and original_messages.strip():
                memory_content = original_messages
                
        elif memory_type == 'profile_v1':
            # 用户画像类型：使用 user_profile
            user_profile = memory_info.get('user_profile', '')
            if user_profile and user_profile != 'null' and str(user_profile).strip() and user_profile.lower() != 'null':
                memory_content = str(user_profile).strip()
        else:
            # 其他类型：尝试通用字段
            memory_val = memory_info.get('memory', '') or memory_info.get('summary', '')
            if memory_val and memory_val != 'null' and str(memory_val).strip():
                memory_content = str(memory_val).strip()
    
    # 如果仍未找到内容，尝试其他字段
    if not memory_content:
        memory_val = item.get('memory', '')
        if memory_val and memory_val != 'null' and str(memory_val).strip():
            memory_content = str(memory_val).strip()
    
    # 最后过滤：确保不是 "null" 字符串
    if memory_content and (memory_content == 'null' or memory_content.strip() == ''):
        memory_content = None
    
    return memory_content


def _build_memory_item(item: dict, memory_content: str) -> dict:
    """
    构建标准化的记忆项
    
    Args:
        item: 原始记忆项
        memory_content: 提取的记忆内容
    
    Returns:
        标准化的记忆项字典
    """
    score = item.get('score', 0)
    session_id = item.get('session_id', '')
    user_id_list = item.get('user_id', [])
    assistant_id_list = item.get('assistant_id', [])
    memory_id = item.get('id', '')
    time_stamp = item.get('time', 0)
    memory_type = item.get('memory_type', 'unknown')
    
    return {
        "content": memory_content,
        "score": float(score) if score else 0.0,
        "memory_type": memory_type,
        "session_id": session_id,
        "user_id": user_id_list[0] if user_id_list else '',
        "assistant_id": assistant_id_list[0] if assistant_id_list else '',
        "memory_id": memory_id,
        "time": time_stamp
    }


# ==================== 画像查询 ====================

def get_profile_by_id(coll, profile_id: str) -> Optional[dict]:
    """
    根据 profile_id 从指定 collection 中查询画像记录
    
    由于 VikingMem SDK 没有直接的 get_profile，这里通过 search_memory 精确过滤
    
    Args:
        coll: Collection 对象
        profile_id: 画像ID
    
    Returns:
        画像的 memory_info 字典，如果未找到则返回 None
    """
    try:
        result = coll.search_memory(
            query="",  # 使用空 query，只依赖 filter 精确过滤
            filter={"profile_id": profile_id, "memory_type": ["profile_v1"]},
            limit=1,
        )
    except VikingMemException as e:
        logger.error(f"【画像查询】VikingMem 异常: {e.message}")
        raise HTTPException(status_code=500, detail=f"查询画像失败: {e.message}")
    except Exception as e:
        logger.error(f"【画像查询】未知异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询画像失败: {str(e)}")
    
    if not result or not isinstance(result, dict):
        return None
    
    data = result.get("data") or {}
    if data.get("count", 0) <= 0:
        return None
    
    result_list = data.get("result_list") or []
    if not result_list:
        return None
    
    # 默认取第一条
    item = result_list[0]
    # VikingMem 返回的画像内容一般在 memory_info 里
    return item.get("memory_info") or {}


# ==================== 记忆信息合并 ====================

def merge_memory_info(original: Optional[dict], updates: Optional[dict]) -> Optional[dict]:
    """
    对画像的 memory_info 做字段级 merge
    
    Args:
        original: 原始画像的 memory_info（可能为 None）
        updates: 本次请求传入的 memory_info（可能为 None）
    
    Returns:
        合并后的 memory_info 字典
    
    规则：
    - 如果 updates 为 None：不修改内容，直接返回 original
    - 否则：original 先拷贝一份，然后用 updates 中的字段逐一覆盖
    """
    if updates is None:
        return original
    
    if original is None:
        original = {}
    
    merged = dict(original)
    for k, v in updates.items():
        merged[k] = v
    
    return merged


# ==================== 信息提取 ====================

def extract_dog_info(dog_memories: List[dict]) -> dict:
    """
    从狗的记忆中提取名字、性格、说话风格等信息
    
    Args:
        dog_memories: 狗的记忆列表
    
    Returns:
        包含 name, character, tone 的字典
    """
    dog_info = {
        "name": "旺财",  # 默认名字
        "character": "活泼、友好、忠诚",
        "tone": "亲切、温暖、略带调皮"
    }
    
    # 从 profile_v1 类型的记忆中提取信息
    for mem in dog_memories:
        content = mem.get('content', '')
        if not content:
            continue
        
        # 提取名字 - 多种模式
        name_patterns = [
            r'名字[是：:]([^，,。.\n]+)',
            r'叫([^，,。.\n]{2,4})',
            r'我是([^，,。.\n]{2,4})',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, content)
            if match:
                potential_name = match.group(1).strip()
                if 2 <= len(potential_name) <= 6:
                    dog_info["name"] = potential_name
                    break
        
        # 提取性格
        char_patterns = [
            r'性格[是：:]([^，,。.\n]+)',
            r'性格[为]([^，,。.\n]+)',
            r'([活泼开朗友好忠诚温顺聪明调皮]+)',
        ]
        for pattern in char_patterns:
            match = re.search(pattern, content)
            if match:
                potential_char = match.group(1).strip()
                if len(potential_char) >= 2:
                    dog_info["character"] = potential_char
                    break
        
        # 提取说话风格
        tone_patterns = [
            r'说话[风格风格是：:]([^，,。.\n]+)',
            r'说话[方式为]([^，,。.\n]+)',
            r'([亲切温暖调皮可爱]+)',
        ]
        for pattern in tone_patterns:
            match = re.search(pattern, content)
            if match:
                potential_tone = match.group(1).strip()
                if len(potential_tone) >= 2:
                    dog_info["tone"] = potential_tone
                    break
    
    return dog_info


def extract_user_nickname(user_memories: List[dict]) -> str:
    """
    从用户记忆中提取昵称
    
    Args:
        user_memories: 用户记忆列表
    
    Returns:
        用户昵称，如果未找到则返回 "朋友"
    """
    nickname = "朋友"  # 默认昵称
    
    for mem in user_memories:
        content = mem.get('content', '')
        if not content:
            continue
        
        # 匹配常见的中文名字模式
        name_patterns = [
            r'名字[是：:]([^，,。.\n]+)',
            r'叫([^，,。.\n]{2,4})',
            r'([张李王刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤])([^，,。.\n]{1,2})',
            r'([^，,。.\n]{2,4})喜欢',  # "张三喜欢"这种模式
        ]
        for pattern in name_patterns:
            match = re.search(pattern, content)
            if match:
                potential_name = match.group(1).strip() if match.groups() else match.group(0).strip()
                # 过滤掉一些明显不是名字的词
                if (2 <= len(potential_name) <= 4 and 
                    potential_name not in ['喜欢', '名字', '性格', '说话', '用户', '朋友']):
                    nickname = potential_name
                    break
        
        if nickname != "朋友":  # 如果找到了名字就退出
            break
    
    return nickname
