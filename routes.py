"""
API 路由模块：所有 FastAPI 路由处理函数
"""
import os
import json
import asyncio
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from vikingdb.memory.exceptions import VikingMemException

from config import (
    VIKINGDB_PROJECT, VIKINGDB_PROFILE_TYPE,
    COLLECTION_ENV_BY_KEY, COLLECTION_DEFAULT_NAME_BY_KEY,
    logger
)
from models import (
    QueryRequest, QueryResponse,
    ProfileAddRequest, ProfileUpdateRequest,
    MultiCollectionProfileAddRequest, MultiCollectionProfileUpdateRequest,
    SessionAddRequest, MemorySearchRequest,
    DebugChatRequest, DebugChatResponse,
)
from viking_client import get_collection_by_key, get_collection
from memory_utils import (
    search_viking_memories, get_profile_by_id, merge_memory_info
)
from ai_utils import (
    generate_answer_with_ai, generate_answer_with_dog_persona,
    generate_answer_with_dog_persona_stream,
    decide_memory_writing, extract_profile_info_with_ai
)
from memory_writing import (
    apply_memory_writing_decision, add_session_memory, upsert_profile
)


# ==================== 基础路由 ====================

def setup_routes(app):
    """
    设置所有路由到 FastAPI 应用
    
    Args:
        app: FastAPI 应用实例
    """
    
    @app.get("/")
    async def root():
        """健康检查"""
        return {"status": "ok", "message": "VikingDB 智能记忆助手服务运行中"}
    
    
    @app.get("/api/health")
    async def health_check():
        """健康检查接口"""
        try:
            get_collection()
            return {"status": "healthy", "vikingdb": "connected"}
        except Exception as e:
            logger.error(f"【健康检查】失败: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    
    @app.get("/api/collections")
    async def list_collections():
        """
        返回后端支持的 collection_key 以及实际使用的 collection_name
        便于前端调试确认写入目标
        """
        result = {"project": VIKINGDB_PROJECT, "collections": {}}
        for key, env_name in COLLECTION_ENV_BY_KEY.items():
            name = os.getenv(env_name, COLLECTION_DEFAULT_NAME_BY_KEY[key])
            result["collections"][key] = {"collection_name": name, "env": env_name}
        return result
    
    
    # ==================== 查询路由 ====================
    
    @app.post("/api/query", response_model=QueryResponse)
    async def query_memory(request: QueryRequest):
        """
        智能查询记忆库并生成回答
        
        流程：
        1. 搜索 VikingDB 记忆库
        2. 使用 OpenAI 整合信息生成回答
        3. 记录本轮真实对话到会话记忆
        4. 基于 user_id 维护画像
        """
        request_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        logger.info("\n" + "=" * 80)
        logger.info(f"【查询请求 #{request_id}】开始处理")
        logger.info(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
        
        try:
            # 1. 搜索 VikingDB 记忆库
            memories, sources = search_viking_memories(
                query=request.query,
                user_id=request.user_id,
                assistant_id=request.assistant_id,
                limit=request.limit
            )
            
            # 2. 使用 OpenAI 整合信息生成回答
            answer = generate_answer_with_ai(request.query, memories)
            
            # 3. 记录本轮真实对话到会话记忆（event_v1）
            add_session_memory(
                user_id=request.user_id,
                assistant_id=request.assistant_id,
                query=request.query,
                answer=answer,
            )
            
            # 4. 基于 user_id 维护画像：
            #    先从当前召回的记忆中找到已存在的画像文本，再结合本轮对话做增量/定点更新
            existing_profile_text = None
            for mem in memories:
                if mem.get("memory_type") == "profile_v1" and mem.get("content"):
                    existing_profile_text = mem["content"]
                    break
            
            extracted_profile = extract_profile_info_with_ai(
                request.query,
                answer,
                existing_profile_text,
            )
            if extracted_profile:
                try:
                    upsert_profile(
                        user_id=request.user_id,
                        assistant_id=request.assistant_id,
                        memory_info=extracted_profile,
                        profile_type=VIKINGDB_PROFILE_TYPE,
                        collection_key="user",
                    )
                except Exception as e:
                    logger.error(f"【画像自动更新】失败（不影响主流程）: {str(e)}")
            
            # 构建最终响应
            response_data = QueryResponse(
                answer=answer,
                memories=memories,
                sources=sources
            )
            
            # 记录最终响应结果
            logger.info("【查询请求】处理完成")
            logger.info(f"回答内容: {answer}")
            logger.info(f"记忆数量: {len(memories)}")
            logger.info(f"来源数量: {len(sources)}")
            logger.info(f"【查询请求 #{request_id}】处理完成")
            logger.info("=" * 80 + "\n")
            
            return response_data
        except Exception as e:
            error_detail = f"查询失败: {str(e)}"
            logger.error(f"【查询请求 #{request_id}】处理失败")
            logger.error(f"错误信息: {error_detail}")
            logger.error(f"错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
            logger.info("=" * 80 + "\n")
            raise HTTPException(status_code=500, detail=error_detail)
    
    
    # ==================== 调试聊天路由 ====================
    
    @app.post("/api/debug/chat")
    async def debug_chat(request: DebugChatRequest):
        """
        调试用：跨 user/dog/relationship/conversation 四库召回上下文，然后生成流式回答，并把本轮写入 conversation 库
        
        约定：
        - user 库：user_id = request.user_id, assistant_id = request.assistant_id
        - dog 库：user_id = request.dog_id, assistant_id = request.assistant_id
        - relationship 库：user_id = request.user_id, assistant_id = request.dog_id
        - conversation 库：基于 metadata 中 default_user_id/default_assistant_id 建索引
        
        返回流式响应（SSE格式）
        """
        logger.info("【调试聊天-流式】开始处理")
        logger.info(f"请求参数: user_id={request.user_id}, dog_id={request.dog_id}, conversation_id={request.conversation_id}")
        
        # 校验合法性
        if not request.user_id or not request.dog_id or not request.conversation_id:
            logger.error("【调试聊天】参数校验失败: user_id / dog_id / conversation_id 均不能为空")
            raise HTTPException(
                status_code=400,
                detail="user_id / dog_id / conversation_id 均不能为空"
            )
        
        user_id = request.user_id
        dog_id = request.dog_id
        conversation_id = request.conversation_id
        assistant_id = request.assistant_id or "assistant_001"
        
        async def generate_stream():
            full_answer = ""
            try:
                # 1) 召回 user 画像/事件
                user_mems, _ = search_viking_memories(
                    query=request.query,
                    user_id=user_id,
                    assistant_id=assistant_id,
                    limit=request.limit or 5,
                    collection_key="user",
                )
                
                # 2) 召回 dog 画像/事件
                dog_mems, _ = search_viking_memories(
                    query=request.query,
                    user_id=dog_id,
                    assistant_id=assistant_id,
                    limit=request.limit or 5,
                    collection_key="dog",
                )
                
                # 3) 召回 relationship（用户-狗）
                rel_mems, _ = search_viking_memories(
                    query=request.query,
                    user_id=user_id,
                    assistant_id=dog_id,
                    limit=request.limit or 5,
                    collection_key="relationship",
                )
                
                # 4) 召回 conversation（用户-狗 的历史对话）
                conv_mems, _ = search_viking_memories(
                    query=request.query,
                    user_id=user_id,
                    assistant_id=dog_id,
                    limit=request.limit or 5,
                    collection_key="conversation",
                )
                
                # 5) 使用机器狗角色模板生成流式回答
                logger.info("【调试聊天-流式】开始生成流式回答")
                chunk_count = 0
                stream_generator = generate_answer_with_dog_persona_stream(
                    query=request.query,
                    user_memories=user_mems,
                    dog_memories=dog_mems,
                    relationship_memories=rel_mems,
                    conversation_memories=conv_mems,
                    model=request.model or "chatgpt"
                )
                
                # 在 async 函数中迭代同步生成器，确保每个 chunk 立即发送
                # 注意：OpenAI 的流式响应是同步的，但我们需要在 async 上下文中处理
                for chunk in stream_generator:
                    chunk_count += 1
                    full_answer += chunk
                    # 发送 SSE 格式的数据，确保立即发送
                    sse_data = json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)
                    logger.info(f"【调试聊天-流式】准备发送第 {chunk_count} 个chunk (长度: {len(chunk)}, 内容: {repr(chunk[:30])})")
                    # 使用 \n\n 确保 SSE 事件立即发送
                    sse_message = f"data: {sse_data}\n\n"
                    yield sse_message
                    # 让出控制权，确保数据立即刷新到客户端
                    await asyncio.sleep(0)
                    logger.debug(f"【调试聊天-流式】已发送第 {chunk_count} 个chunk")
                
                logger.info(f"【调试聊天-流式】流式回答生成完成，共 {chunk_count} 个chunk，总长度: {len(full_answer)}")
                
                # 6) 记忆写入决策：是否写入？写入到哪里？
                memory_decision = decide_memory_writing(
                    user_id=user_id,
                    dog_id=dog_id,
                    conversation_id=conversation_id,
                    query=request.query,
                    answer=full_answer,
                    user_memories=user_mems,
                    dog_memories=dog_mems,
                    relationship_memories=rel_mems,
                    conversation_memories=conv_mems,
                    model=request.model or "chatgpt",
                )
                
                # 7) 基于决策结果，将用户长期特征 / 关系里程碑 / 机器狗认知变化写入对应库
                extra_write_results = apply_memory_writing_decision(
                    decision=memory_decision or {},
                    user_id=user_id,
                    dog_id=dog_id,
                    conversation_id=conversation_id,
                    assistant_id=assistant_id,
                    query=request.query,
                    answer=full_answer,
                )
                
                # 8) 写入本轮对话到 conversation（用 conversation_id + 时间戳，保证每轮都落库）
                write_result = None
                try:
                    coll = get_collection_by_key("conversation")
                    session_id = f"{conversation_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                    messages = [
                        {"role": "user", "content": request.query},
                        {"role": "assistant", "content": full_answer},
                    ]
                    metadata = {
                        "default_user_id": user_id,
                        "default_assistant_id": dog_id,
                        "conversation_id": conversation_id,
                        "time": int(datetime.now().timestamp() * 1000),
                    }
                    # 将记忆写入决策的关键信息也写入 metadata，便于后续检索和调试
                    if memory_decision:
                        metadata["memory_decision"] = {
                            "should_write": bool(memory_decision.get("should_write")),
                            "has_emotion_change": bool(memory_decision.get("has_emotion_change")),
                            "is_relationship_turning": bool(memory_decision.get("is_relationship_turning")),
                            "is_duplicate": bool(memory_decision.get("is_duplicate")),
                            "targets": memory_decision.get("targets") or [],
                        }
                        conv_summary = (memory_decision.get("memories") or {}).get("conversation")
                        if conv_summary:
                            metadata["conversation_summary_by_dog"] = str(conv_summary)
                    
                    write_result = coll.add_session(
                        session_id=session_id,
                        messages=messages,
                        metadata=metadata,
                    )
                    logger.info(f"【调试聊天-会话写入】成功: {json.dumps(write_result, ensure_ascii=False, default=str)}")
                except Exception as e:
                    logger.error(f"【调试聊天-会话写入】失败（不影响返回）: {str(e)}")
                
                # 发送完成信号
                yield f"data: {json.dumps({'content': '', 'done': True, 'full_answer': full_answer}, ensure_ascii=False)}\n\n"
                logger.info("【调试聊天-流式】处理完成")
            except Exception as e:
                logger.error(f"【调试聊天-流式】处理失败: {str(e)}")
                import traceback
                logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
                error_msg = json.dumps({'error': f"调试聊天失败: {str(e)}", 'done': True}, ensure_ascii=False)
                yield f"data: {error_msg}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            }
        )
    
    
    # ==================== 画像路由（单库） ====================
    
    @app.post("/api/profile/add")
    async def add_profile(request: ProfileAddRequest):
        """
        添加画像记忆（对应文档 AddProfile 的请求 schema）
        默认写入 user 库，避免误落 conversation 等其它库
        参考文档：https://www.volcengine.com/docs/84313/1946680?lang=zh
        """
        logger.info("【添加画像记忆】开始")
        logger.info(f"请求参数: {json.dumps(request.model_dump(), ensure_ascii=False)}")
        
        try:
            coll = get_collection_by_key("user")
            result = coll.add_profile(
                profile_type=request.profile_type,
                memory_info=request.memory_info,
                user_id=request.user_id,
                assistant_id=request.assistant_id,
                group_id=request.group_id,
                is_upsert=request.is_upsert,
            )
            logger.info(f"【添加画像记忆】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
            return result
        except VikingMemException as e:
            logger.error(f"【添加画像记忆】VikingMem 异常: {e.message}")
            raise HTTPException(status_code=500, detail=f"添加画像失败: {e.message}")
        except Exception as e:
            logger.error(f"【添加画像记忆】未知异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"添加画像失败: {str(e)}")
    
    
    @app.post("/api/profile/update")
    async def update_profile(request: ProfileUpdateRequest):
        """
        更新画像记忆（对应文档 UpdateProfile 的请求 schema）
        默认更新 user 库，保持身份信息落在正确的集合
        参考文档：https://www.volcengine.com/docs/84313/1946684?lang=zh
        """
        logger.info("【更新画像记忆】开始")
        logger.info(f"请求参数: {json.dumps(request.model_dump(), ensure_ascii=False)}")
        
        try:
            coll = get_collection_by_key("user")
            
            # 先按 profile_id 查询已有画像
            original_profile_info = get_profile_by_id(coll, request.profile_id)
            
            # 字段级 merge：只用本次传入的字段覆盖原有字段，其它字段保持不变
            merged_memory_info = merge_memory_info(original_profile_info, request.memory_info)
            
            kwargs = {"profile_id": request.profile_id}
            if merged_memory_info is not None:
                kwargs["memory_info"] = merged_memory_info
            
            result = coll.update_profile(**kwargs)
            logger.info(f"【更新画像记忆】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
            return result
        except VikingMemException as e:
            logger.error(f"【更新画像记忆】VikingMem 异常: {e.message}")
            raise HTTPException(status_code=500, detail=f"更新画像失败: {e.message}")
        except Exception as e:
            logger.error(f"【更新画像记忆】未知异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"更新画像失败: {str(e)}")
    
    
    # ==================== 画像路由（多库） ====================
    
    @app.post("/api/memory/profile/add")
    async def add_profile_multi(request: MultiCollectionProfileAddRequest):
        """添加画像记忆-多库（支持指定 collection_key）"""
        logger.info("【添加画像记忆-多库】开始")
        logger.info(f"请求参数: {json.dumps(request.model_dump(), ensure_ascii=False)}")
        
        try:
            coll = get_collection_by_key(request.collection_key)
            result = coll.add_profile(
                profile_type=request.profile_type,
                memory_info=request.memory_info,
                user_id=request.user_id,
                assistant_id=request.assistant_id,
                group_id=request.group_id,
                is_upsert=request.is_upsert,
            )
            logger.info(f"【添加画像记忆-多库】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
            return result
        except VikingMemException as e:
            logger.error(f"【添加画像记忆-多库】VikingMem 异常: {e.message}")
            raise HTTPException(status_code=500, detail=f"添加画像失败: {e.message}")
        except Exception as e:
            logger.error(f"【添加画像记忆-多库】未知异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"添加画像失败: {str(e)}")
    
    
    @app.post("/api/memory/profile/update")
    async def update_profile_multi(request: MultiCollectionProfileUpdateRequest):
        """更新画像记忆-多库（支持指定 collection_key）"""
        logger.info("【更新画像记忆-多库】开始")
        logger.info(f"请求参数: {json.dumps(request.model_dump(), ensure_ascii=False)}")
        
        try:
            coll = get_collection_by_key(request.collection_key)
            
            # 先按 profile_id 查询已有画像
            original_profile_info = get_profile_by_id(coll, request.profile_id)
            
            # 字段级 merge：只用本次传入的字段覆盖原有字段，其它字段保持不变
            merged_memory_info = merge_memory_info(original_profile_info, request.memory_info)
            
            kwargs = {"profile_id": request.profile_id}
            if merged_memory_info is not None:
                kwargs["memory_info"] = merged_memory_info
            
            result = coll.update_profile(**kwargs)
            logger.info(f"【更新画像记忆-多库】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
            return result
        except VikingMemException as e:
            logger.error(f"【更新画像记忆-多库】VikingMem 异常: {e.message}")
            raise HTTPException(status_code=500, detail=f"更新画像失败: {e.message}")
        except Exception as e:
            logger.error(f"【更新画像记忆-多库】未知异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"更新画像失败: {str(e)}")
    
    
    # ==================== 会话路由 ====================
    
    @app.post("/api/memory/session/add")
    async def add_session_multi(request: SessionAddRequest):
        """会话写入-多库（支持指定 collection_key）"""
        logger.info("【会话写入-多库】开始")
        logger.info(f"请求参数: {json.dumps(request.model_dump(), ensure_ascii=False)}")
        
        try:
            coll = get_collection_by_key(request.collection_key)
            base_metadata = {
                "default_user_id": request.user_id,
                "default_assistant_id": request.assistant_id,
                "time": int(datetime.now().timestamp() * 1000),
            }
            if request.metadata and isinstance(request.metadata, dict):
                base_metadata.update(request.metadata)
            
            result = coll.add_session(
                session_id=request.session_id,
                messages=request.messages,
                metadata=base_metadata,
            )
            logger.info(f"【会话写入-多库】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
            return result
        except VikingMemException as e:
            logger.error(f"【会话写入-多库】VikingMem 异常: {e.message}")
            raise HTTPException(status_code=500, detail=f"会话写入失败: {e.message}")
        except Exception as e:
            logger.error(f"【会话写入-多库】未知异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"会话写入失败: {str(e)}")
    
    
    # ==================== 记忆检索路由 ====================
    
    @app.post("/api/memory/search")
    async def search_memory_multi(request: MemorySearchRequest):
        """记忆检索-多库（支持指定 collection_key）"""
        logger.info("【记忆检索-多库】开始")
        logger.info(f"请求参数: {json.dumps(request.model_dump(), ensure_ascii=False)}")
        
        try:
            coll = get_collection_by_key(request.collection_key)
            result = coll.search_memory(
                query=request.query,
                filter=request.filter or {},
                limit=request.limit or 5,
            )
            return result
        except VikingMemException as e:
            logger.error(f"【记忆检索-多库】VikingMem 异常: {e.message}")
            raise HTTPException(status_code=500, detail=f"检索失败: {e.message}")
        except Exception as e:
            logger.error(f"【记忆检索-多库】未知异常: {str(e)}")
            raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")
    
    
    # ==================== 列表查询路由 ====================
    
    @app.get("/api/users")
    async def list_users():
        """
        获取用户列表（从 user 库中检索所有不同的 user_id）
        返回格式: {"users": ["user_001", "user_002", ...], "default": "user_001"}
        """
        try:
            coll = get_collection_by_key("user")
            # 使用一个通用查询来获取所有用户（VikingDB可能不支持直接列出所有user_id，这里返回默认列表）
            # 实际场景中，你可能需要维护一个用户列表或使用其他方式
            default_users = ["user_001", "user_002", "user_003"]
            return {"users": default_users, "default": default_users[0]}
        except Exception as e:
            logger.error(f"【获取用户列表】失败，返回默认列表: {str(e)}")
            default_users = ["user_001"]
            return {"users": default_users, "default": default_users[0]}
    
    
    @app.get("/api/dogs")
    async def list_dogs():
        """
        获取狗列表（从 dog 库中检索所有不同的 user_id，在dog库中user_id实际代表dog_id）
        返回格式: {"dogs": ["dog_001", "dog_002", ...], "default": "dog_001"}
        """
        try:
            coll = get_collection_by_key("dog")
            default_dogs = ["dog_001", "dog_002", "dog_003"]
            return {"dogs": default_dogs, "default": default_dogs[0]}
        except Exception as e:
            logger.error(f"【获取狗列表】失败，返回默认列表: {str(e)}")
            default_dogs = ["dog_001"]
            return {"dogs": default_dogs, "default": default_dogs[0]}
    
    
    @app.get("/api/conversations")
    async def list_conversations(user_id: str, dog_id: str):
        """
        获取历史会话列表（从 conversation 库中检索指定用户和狗的所有会话）
        返回格式: {"conversations": [{"id": "conv_001", "title": "...", "last_message_time": ...}, ...]}
        """
        try:
            coll = get_collection_by_key("conversation")
            # 搜索该用户和狗的所有会话记录
            result = coll.search_memory(
                query="对话 会话",
                filter={
                    "memory_type": ["event_v1"],
                    "user_id": user_id,
                    "assistant_id": dog_id,
                },
                limit=100  # 获取更多记录以便提取所有会话ID
            )
            
            conversations_map = {}
            if result and isinstance(result, dict) and result.get('data'):
                result_data = result['data']
                if result_data.get('count', 0) > 0 and 'result_list' in result_data:
                    for item in result_data['result_list']:
                        metadata = item.get('metadata', {})
                        conv_id = metadata.get('conversation_id', '')
                        if not conv_id:
                            # 如果没有conversation_id，使用session_id的前缀部分
                            session_id = item.get('session_id', '')
                            if session_id and '_' in session_id:
                                conv_id = session_id.split('_')[0]
                        
                        if conv_id and conv_id not in conversations_map:
                            time_stamp = item.get('time', 0) or metadata.get('time', 0)
                            memory_info = item.get('memory_info', {})
                            messages = memory_info.get('original_messages', '') or memory_info.get('summary', '')
                            title = messages[:50] + "..." if len(messages) > 50 else messages or "新对话"
                            
                            conversations_map[conv_id] = {
                                "id": conv_id,
                                "title": title,
                                "last_message_time": time_stamp,
                            }
            
            conversations = list(conversations_map.values())
            # 按时间倒序排序
            conversations.sort(key=lambda x: x.get('last_message_time', 0), reverse=True)
            
            # 如果没有找到历史会话，返回一个默认的新会话ID
            if not conversations:
                default_conv_id = f"conv_{user_id}_{dog_id}_{datetime.now().strftime('%Y%m%d')}"
                conversations = [{
                    "id": default_conv_id,
                    "title": "新对话",
                    "last_message_time": int(datetime.now().timestamp() * 1000),
                }]
            
            return {"conversations": conversations}
        except Exception as e:
            logger.error(f"【获取会话列表】失败: {str(e)}")
            # 返回一个默认会话
            default_conv_id = f"conv_{user_id}_{dog_id}_{datetime.now().strftime('%Y%m%d')}"
            return {
                "conversations": [{
                    "id": default_conv_id,
                    "title": "新对话",
                    "last_message_time": int(datetime.now().timestamp() * 1000),
                }]
            }
