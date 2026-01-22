"""
记忆写入模块：根据决策结果实际写入记忆库
"""
import os
import json
import re
import logging
from typing import Dict, Optional
from datetime import datetime
from viking_client import get_collection_by_key
from config import VIKINGDB_PROFILE_TYPE, logger
from memory_utils import search_viking_memories
from ai_utils import summarize_profile_with_ai


def apply_memory_writing_decision(
    decision: dict,
    user_id: str,
    dog_id: str,
    conversation_id: str,
    assistant_id: str,
    query: str,
    answer: str,
) -> dict:
    """
    根据决策结果实际落库
    
    映射关系：
    - 用户长期特征        → user collection（profile_v1）
    - 关系里程碑          → relationship collection（profile_v1）
    - 当前情绪 / 事件     → conversation collection（通过会话写入，元数据里会额外标记）
    - 机器狗认知变化      → dog collection（profile_v1）
    
    这里仅负责 user/dog/relationship 三类的画像写入；
    conversation 相关的信息会在 debug_chat 的会话写入 metadata 中携带。
    
    Args:
        decision: 记忆写入决策结果
        user_id: 用户ID
        dog_id: 狗ID
        conversation_id: 对话ID
        assistant_id: 助手ID
        query: 用户问题
        answer: 机器狗回答
    
    Returns:
        各类写入的结果字典（便于调试）
    """
    results: dict = {
        "user": None,
        "relationship": None,
        "dog": None,
    }

    if not decision:
        return results

    should_write = bool(decision.get("should_write"))
    is_duplicate = bool(decision.get("is_duplicate"))
    targets = decision.get("targets") or []
    memories = decision.get("memories") or {}

    # === 规则兜底：如果本轮对话中用户明确自报姓名，则强制写入 user 画像 ===
    user_name = _extract_user_name_from_conversation(query, answer)
    if user_name:
        # 确保 targets 中包含 user
        if "user" not in [str(t).lower().strip() for t in targets]:
            targets = list(targets) + ["user"]
        # 若 AI 决策未给出 user 文本，这里补一条稳定的身份描述
        memories = dict(memories)
        if not str(memories.get("user", "")).strip():
            memories["user"] = f"用户自称名字为「{user_name}」，需要按这个名字称呼他/她。"
        # 即使原决策认为不写入，这类身份信息也应强制写入
        should_write = True
        is_duplicate = False
        logger.info(f"【记忆写入】检测到用户自报姓名: {user_name}，强制写入 user 画像")

    if not should_write or is_duplicate:
        logger.info(f"【记忆写入】跳过写入: should_write={should_write}, is_duplicate={is_duplicate}")
        return results

    # 规范化 targets
    norm_targets = {str(t).lower().strip() for t in targets}

    # 1) 用户长期特征 → user collection
    if "user" in norm_targets:
        new_profile_text = str(memories.get("user", "")).strip()
        if new_profile_text:
            try:
                # 获取历史画像
                old_profile_text = None
                try:
                    user_mems, _ = search_viking_memories(
                        query="用户画像",
                        user_id=user_id,
                        assistant_id=assistant_id or "assistant_001",
                        limit=5,
                        collection_key="user",
                        extra_filter={"memory_type": ["profile_v1"]}
                    )
                    # 从搜索结果中提取历史画像（优先取profile_v1类型）
                    for mem in user_mems:
                        if mem.get("memory_type") == "profile_v1" and mem.get("content"):
                            old_profile_text = mem.get("content")
                            logger.info(f"【记忆写入-user】找到历史画像: {old_profile_text[:100]}...")
                            break
                except Exception as e:
                    logger.warning(f"【记忆写入-user】获取历史画像失败（继续使用新画像）: {str(e)}")
                
                # 将历史画像和新画像交给AI进行总结
                summarized_profile = None
                if old_profile_text:
                    try:
                        summarized_profile = summarize_profile_with_ai(
                            old_profile=old_profile_text,
                            new_profile=new_profile_text,
                            model="chatgpt"  # 可以根据需要改为deepseek
                        )
                        if summarized_profile:
                            logger.info(f"【记忆写入-user】AI总结完成: {summarized_profile[:100]}...")
                        else:
                            logger.warning("【记忆写入-user】AI总结失败，使用新画像")
                            summarized_profile = new_profile_text
                    except Exception as e:
                        logger.error(f"【记忆写入-user】AI总结异常，使用新画像: {str(e)}")
                        summarized_profile = new_profile_text
                else:
                    # 没有历史画像，直接使用新画像
                    logger.info("【记忆写入-user】无历史画像，直接使用新画像")
                    summarized_profile = new_profile_text
                
                # 使用总结后的画像写入
                coll_user = get_collection_by_key("user")
                payload = {
                    "user_profile": summarized_profile,
                }
                res_user = coll_user.add_profile(
                    profile_type=VIKINGDB_PROFILE_TYPE,
                    memory_info=payload,
                    user_id=user_id,
                    assistant_id=assistant_id or "assistant_001",
                    is_upsert=True,
                )
                logger.info(f"【记忆写入-user】成功: {json.dumps(res_user, ensure_ascii=False, default=str)}")
                results["user"] = res_user
            except Exception as e:
                logger.error(f"【记忆写入-user】失败: {str(e)}")

    # 2) 关系里程碑 → relationship collection
    if "relationship" in norm_targets:
        text = str(memories.get("relationship", "")).strip()
        if text:
            try:
                coll_rel = get_collection_by_key("relationship")
                payload = {
                    "user_profile": text,
                }
                # 在 relationship 库中，约定 user_id=用户，assistant_id=dog_id
                res_rel = coll_rel.add_profile(
                    profile_type=VIKINGDB_PROFILE_TYPE,
                    memory_info=payload,
                    user_id=user_id,
                    assistant_id=dog_id,
                    is_upsert=True,
                )
                logger.info(f"【记忆写入-relationship】成功: {json.dumps(res_rel, ensure_ascii=False, default=str)}")
                results["relationship"] = res_rel
            except Exception as e:
                logger.error(f"【记忆写入-relationship】失败: {str(e)}")

    # 3) 机器狗认知变化 → dog collection
    if "dog" in norm_targets:
        text = str(memories.get("dog", "")).strip()
        if text:
            try:
                coll_dog = get_collection_by_key("dog")
                payload = {
                    "user_profile": text,
                }
                # 在 dog 库中，约定 user_id=dog_id
                res_dog = coll_dog.add_profile(
                    profile_type=VIKINGDB_PROFILE_TYPE,
                    memory_info=payload,
                    user_id=dog_id,
                    assistant_id=assistant_id or "assistant_001",
                    is_upsert=True,
                )
                logger.info(f"【记忆写入-dog】成功: {json.dumps(res_dog, ensure_ascii=False, default=str)}")
                results["dog"] = res_dog
            except Exception as e:
                logger.error(f"【记忆写入-dog】失败: {str(e)}")

    return results


def _extract_user_name_from_conversation(query: str, answer: str) -> Optional[str]:
    """
    从对话中提取用户自报的姓名
    
    Args:
        query: 用户问题
        answer: 机器狗回答
    
    Returns:
        提取到的姓名，如果未找到则返回 None
    """
    try:
        text_for_name = f"{query}\n{answer}"
        name_patterns = [
            r"记住我叫([^\s，,。.!？?]{2,6})",
            r"我叫([^\s，,。.!？?]{2,6})",
            r"我的名字[是为]?([^\s，,。.!？?]{2,6})",
        ]
        for p in name_patterns:
            m = re.search(p, text_for_name)
            if m:
                candidate = m.group(1).strip()
                if 1 < len(candidate) <= 6:
                    return candidate
    except Exception:
        pass
    return None


def add_session_memory(
    user_id: str,
    assistant_id: str,
    query: str,
    answer: str,
    collection_key: str = "default"
):
    """
    将本轮真实对话写入会话记忆（event_v1）
    
    Args:
        user_id: 用户ID
        assistant_id: 助手ID
        query: 用户问题
        answer: 助手回答
        collection_key: 集合标识
    
    Returns:
        写入结果，如果失败则返回 None
    """
    try:
        coll = get_collection_by_key(collection_key)
        # 使用 user_id + 时间戳 作为一个简单的 session_id
        session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        messages = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": answer},
        ]
        metadata = {
            "default_user_id": user_id,
            "default_assistant_id": assistant_id,
            "time": int(datetime.now().timestamp() * 1000),
        }
        logger.info(f"【会话写入】开始, session_id={session_id}, collection_key={collection_key}")
        result = coll.add_session(
            session_id=session_id,
            messages=messages,
            metadata=metadata,
        )
        logger.info(f"【会话写入】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
        return result
    except Exception as e:
        # 会话写入失败不影响主流程，只打日志
        logger.error(f"【会话写入】失败（不影响主流程）: {str(e)}")
        return None


def upsert_profile(
    user_id: str,
    assistant_id: str,
    memory_info: dict,
    profile_type: str = "profile_v1",
    collection_key: str = "user",
):
    """
    基于 user_id 进行画像 upsert：调用 add_profile(is_upsert=True)
    
    Args:
        user_id: 用户ID
        assistant_id: 助手ID
        memory_info: 记忆信息字典
        profile_type: 画像类型
        collection_key: 集合标识
    
    Returns:
        写入结果
    """
    target_key = collection_key or "user"
    coll = get_collection_by_key(target_key)
    result = coll.add_profile(
        profile_type=profile_type,
        memory_info=memory_info,
        user_id=user_id,
        assistant_id=assistant_id,
        is_upsert=True,
    )
    logger.info(f"【画像更新】add_profile(is_upsert=True) 完成: {json.dumps(result, ensure_ascii=False, default=str)}")
    return result
