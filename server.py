"""
VikingDB + OpenAI 智能记忆查询服务器
"""
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from openai import OpenAI
from vikingdb import IAM
from vikingdb.memory import VikingMem
from vikingdb.memory.exceptions import VikingMemException

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置日志
def setup_logging():
    """配置日志系统"""
    # 创建logs目录
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

app = FastAPI(title="VikingDB 智能记忆助手")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 OpenAI 客户端
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("请设置环境变量 OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

# 初始化 VikingDB 客户端
def init_viking_client():
    """初始化 VikingDB 客户端"""
    ak = os.getenv("VIKINGDB_AK")
    sk = os.getenv("VIKINGDB_SK")
    if not ak or not sk:
        raise ValueError("请设置环境变量 VIKINGDB_AK 和 VIKINGDB_SK")
    _auth = IAM(ak=ak, sk=sk)
    
    client = VikingMem(
        host="api-knowledgebase.mlp.cn-beijing.volces.com",
        region="cn-beijing",
        auth=_auth,
        scheme="http",
    )
    return client

# 全局变量存储客户端和集合
viking_client = None
collection = None

def get_collection():
    """获取或初始化集合"""
    global viking_client, collection
    if viking_client is None:
        viking_client = init_viking_client()
    
    if collection is None:
        collection_name = os.getenv("VIKINGDB_COLLECTION", "dogbot")
        project_name = os.getenv("VIKINGDB_PROJECT", "default")
        try:
            collection = viking_client.get_collection(
                collection_name=collection_name,
                project_name=project_name
            )
        except VikingMemException as e:
            raise HTTPException(status_code=500, detail=f"无法获取集合: {str(e)}")
    
    return collection

# 请求模型
class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "user_001"
    assistant_id: Optional[str] = "assistant_001"
    limit: Optional[int] = 5


class ProfileAddRequest(BaseModel):
    """
    添加画像记忆的入参，尽量贴合官方 AddProfile 文档的 scheme：
    - 必填：profile_type、memory_info、user_id
    - 可选：assistant_id、group_id、is_upsert
    集合信息在服务端通过 get_collection() 统一管理。
    """
    profile_type: str = "profile_v1"  # 对应文档中的 profile_type，例如 "sys_profile_v1" 或自定义
    memory_info: dict                  # 对应文档中的 memory_info，结构需与记忆库中定义的一致
    user_id: str                       # 文档中的 user_id
    assistant_id: Optional[str] = "assistant_001"
    group_id: Optional[str] = None
    is_upsert: Optional[bool] = False


class ProfileUpdateRequest(BaseModel):
    """
    更新画像记忆的入参，贴合官方 UpdateProfile 文档的 scheme：
    - 必填：profile_id
    - 可选：memory_info（不传则只触发记录但不更新内容）
    """
    profile_id: str                    # 需要更新的画像记忆 id
    memory_info: Optional[dict] = None

class QueryResponse(BaseModel):
    answer: str
    memories: List[dict]
    sources: List[str]

def search_viking_memories(query: str, user_id: str, assistant_id: str, limit: int = 5):
    """搜索 VikingDB 记忆库"""
    # 记录查询参数
    query_params = {
        "query": query,
        "user_id": user_id,
        "assistant_id": assistant_id,
        "limit": limit
    }
    logger.info(f"【VikingDB查询请求】: {json.dumps(query_params, ensure_ascii=False, indent=2)}")
    
    try:
        coll = get_collection()
        filter_params = {
            "memory_type": ["profile_v1", "event_v1"],
            "user_id": user_id,
            "assistant_id": assistant_id
        }
        logger.info(f"过滤条件: {json.dumps(filter_params, ensure_ascii=False, indent=2)}")
        
        result = coll.search_memory(
            query=query,
            filter=filter_params,
            limit=limit
        )
        
        # 记录原始响应结果
        logger.info(f"【VikingDB原始响应】: {json.dumps(result, ensure_ascii=False, indent=2, default=str)}")
        
        memories = []
        sources = []
        
        if result and isinstance(result, dict) and result.get('data'):
            result_data = result['data']
            count = result_data.get('count', 0)
            logger.info(f"找到 {count} 条记忆记录")
            
            if count > 0 and 'result_list' in result_data:
                for idx, item in enumerate(result_data['result_list'], 1):
                    logger.info(f"--- 处理第 {idx} 条记录 ---")
                    logger.info(f"原始记录: {json.dumps(item, ensure_ascii=False, indent=2, default=str)}")
                    
                    # 根据实际响应结构解析数据
                    memory_content = None
                    memory_type = item.get('memory_type', 'unknown')
                    memory_info = item.get('memory_info', {})
                    
                    # 根据记忆类型解析不同的字段
                    if isinstance(memory_info, dict):
                        if memory_type == 'event_v1':
                            # 事件类型：优先使用 summary，其次使用 original_messages
                            summary = memory_info.get('summary', '')
                            original_messages = memory_info.get('original_messages', '')
                            # 过滤掉 "null" 字符串和空值
                            if summary and summary != 'null' and summary.strip():
                                memory_content = summary
                            elif original_messages and original_messages != 'null' and original_messages.strip():
                                memory_content = original_messages
                        elif memory_type == 'profile_v1':
                            # 用户画像类型：使用 user_profile
                            user_profile = memory_info.get('user_profile', '')
                            # 处理 "null" 字符串和空值的情况
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
                    
                    if memory_content:
                        # 提取其他信息
                        score = item.get('score', 0)
                        session_id = item.get('session_id', '')
                        user_id_list = item.get('user_id', [])
                        assistant_id_list = item.get('assistant_id', [])
                        memory_id = item.get('id', '')
                        time_stamp = item.get('time', 0)
                        
                        memory_item = {
                            "content": memory_content,
                            "score": float(score) if score else 0.0,
                            "memory_type": memory_type,
                            "session_id": session_id,
                            "user_id": user_id_list[0] if user_id_list else '',
                            "assistant_id": assistant_id_list[0] if assistant_id_list else '',
                            "memory_id": memory_id,
                            "time": time_stamp
                        }
                        memories.append(memory_item)
                        sources.append(memory_content[:100] + ("..." if len(memory_content) > 100 else ""))
                        
                        logger.info(f"提取的记忆内容: {memory_content[:200]}...")
                        logger.info(f"相关性分数: {score}, 记忆类型: {memory_type}, 会话ID: {session_id}")
                    else:
                        logger.warning(f"第 {idx} 条记录未找到有效记忆内容")
            else:
                logger.info("结果列表为空")
        else:
            logger.info("未找到相关记忆数据")
        
        # 记录处理后的结果
        logger.info(f"记忆列表: {json.dumps(memories, ensure_ascii=False, indent=2)}")
        
        return memories, sources
    except Exception as e:
        error_msg = f"搜索记忆库失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"错误详情: {json.dumps({'error': str(e), 'type': type(e).__name__}, ensure_ascii=False)}")
        import traceback
        logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
        return [], []

def generate_answer_with_ai(query: str, memories: List[dict]) -> str:
    """使用 OpenAI 整合记忆库知识生成回答"""
    logger.info("【OpenAI生成回答】")
    logger.info(f"用户问题: {query}")
    logger.info(f"使用的记忆数量: {len(memories)}")
    
    # 构建上下文
    context_parts = []
    if memories:
        context_parts.append("=== 相关记忆库信息 ===")
        for i, mem in enumerate(memories, 1):
            context_parts.append(f"\n记忆 {i} (相关性: {mem.get('score', 0):.2f}):")
            context_parts.append(mem.get('content', ''))
    
    context = "\n".join(context_parts) if context_parts else "暂无相关记忆库信息。"
    
    # 构建提示词
    system_prompt = """你是一个智能助手，能够基于用户的记忆库信息回答问题。
请根据提供的记忆库信息，结合你的知识，给出准确、友好、有帮助的回答。
如果记忆库信息与问题相关，优先使用记忆库中的信息。
如果记忆库中没有相关信息，可以基于你的通用知识回答，但要说明这是基于通用知识。"""
    
    user_prompt = f"""用户问题：{query}

{context}

请基于以上信息回答用户的问题。回答要自然、友好、准确。"""
    
    # 记录OpenAI请求参数
    openai_request = {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 500,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
    logger.info(f"OpenAI请求参数: {json.dumps(openai_request, ensure_ascii=False, indent=2)}")
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # 记录OpenAI响应
        answer = response.choices[0].message.content
        logger.info("【OpenAI响应结果】")
        logger.info(f"生成的回答: {answer}")
        logger.info(f"响应元数据: 模型={response.model}, 使用tokens={response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")
        
        return answer
    except Exception as e:
        error_msg = f"抱歉，AI 服务暂时不可用: {str(e)}"
        logger.error(f"OpenAI调用失败: {str(e)}")
        logger.error(f"错误详情: {json.dumps({'error': str(e), 'type': type(e).__name__}, ensure_ascii=False)}")
        return error_msg


def extract_profile_info_with_ai(query: str, answer: str, old_profile: Optional[str]) -> Optional[dict]:
    """
    从本轮对话中提取画像信息，返回 memory_info（dict），格式需与记忆库 schema 一致。
    这里输出 user_profile 文本串，若没有可提取的信息则返回 None。
    """
    system_prompt = """你是一个从多轮对话中维护用户画像的助手。
你会拿到“旧画像文本”和“本轮对话（用户提问与助手回复）”：
1. 如果本轮没有出现任何新的或冲突的画像信息，返回：{"has_new": false}.
2. 如果有新的或需要修改的画像信息，请在保留旧画像中未被改变信息的前提下，生成一份“更新后的完整画像文本”：
   - 以中文文本串描述，可以是若干条目或自然段。
   - 对于明确被新信息覆盖的字段（如年龄从 28 变成 29），请在画像中使用最新值。
   - 旧画像中未被提及的内容要尽量保留，避免丢失。
3. 此时请返回：{"has_new": true, "updated_profile": "更新后的完整画像文本"}。
注意：你的输出必须是单个 JSON 对象，不能包含多余说明文字。"""

    user_prompt = f"""【旧画像】:
{old_profile or "（无历史画像）"}

【用户提问】:
{query}

【助手回复】:
{answer}

请按系统指令返回 JSON。"""
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        content = resp.choices[0].message.content.strip()
        logger.info(f"【画像提取】AI 原始输出: {content}")
        data = json.loads(content)
        if not isinstance(data, dict) or not data.get("has_new"):
            return None
        updated_profile = data.get("updated_profile")
        if not updated_profile or not str(updated_profile).strip():
            return None
        return {"user_profile": str(updated_profile).strip()}
    except Exception as e:
        logger.warning(f"【画像提取】失败，跳过本轮更新: {str(e)}")
        return None


def upsert_profile(user_id: str, assistant_id: str, memory_info: dict, profile_type: str = "profile_v1"):
    """
    基于 user_id 进行画像 upsert：调用 add_profile(is_upsert=True)。
    profile_id 由后端管理，不需要前端提供。
    """
    coll = get_collection()
    result = coll.add_profile(
        profile_type=profile_type,
        memory_info=memory_info,
        user_id=user_id,
        assistant_id=assistant_id,
        is_upsert=True,
    )
    logger.info(f"【画像更新】add_profile(is_upsert=True) 完成: {json.dumps(result, ensure_ascii=False, default=str)}")
    return result


def add_session_memory(user_id: str, assistant_id: str, query: str, answer: str):
    """
    将本轮真实对话写入会话记忆（event_v1），方便后续做会话召回。
    注意：VikingDB 的 memory_type 一般由后端按 schema 管理，这里只负责调用 add_session。
    """
    try:
        coll = get_collection()
        # 使用 user_id + 时间戳 作为一个简单的 session_id；如果你有业务侧会话ID，可以替换这里
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
        logger.info(f"【会话写入】开始, session_id={session_id}")
        result = coll.add_session(
            session_id=session_id,
            messages=messages,
            metadata=metadata,
        )
        logger.info(f"【会话写入】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
        return result
    except Exception as e:
        # 会话写入失败不影响主流程，只打日志
        logger.warning(f"【会话写入】失败（不影响主流程）: {str(e)}")
        return None

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "VikingDB 智能记忆助手服务运行中"}

@app.post("/api/query", response_model=QueryResponse)
async def query_memory(request: QueryRequest):
    """智能查询记忆库并生成回答"""
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
                    profile_type=os.getenv("VIKINGDB_PROFILE_TYPE", "profile_v1"),
                )
            except Exception as e:
                logger.warning(f"【画像自动更新】失败（不影响主流程）: {str(e)}")
        
        # 构建最终响应
        response_data = QueryResponse(
            answer=answer,
            memories=memories,
            sources=sources
        )
        
        # 记录最终响应结果
        logger.info("【最终响应结果】")
        logger.info(f"回答内容: {answer}")
        logger.info(f"记忆数量: {len(memories)}")
        logger.info(f"来源数量: {len(sources)}")
        logger.info(f"完整响应: {json.dumps(response_data.dict(), ensure_ascii=False, indent=2)}")
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


@app.post("/api/profile/add")
async def add_profile(request: ProfileAddRequest):
    """
    添加画像记忆（对应文档 AddProfile 的请求 schema）
    - URL: /api/memory/profile/add
    - Method: POST
    本服务封装集合信息，前端只需关心画像内容与用户标识。
    参考文档：
    https://www.volcengine.com/docs/84313/1946680?lang=zh
    """
    logger.info("【添加画像记忆】开始")
    logger.info(f"请求参数: {request.json(ensure_ascii=False)}")

    try:
        coll = get_collection()
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
    - URL: /api/memory/profile/update
    - Method: POST
    参考文档：
    https://www.volcengine.com/docs/84313/1946684?lang=zh
    """
    logger.info("【更新画像记忆】开始")
    logger.info(f"请求参数: {request.json(ensure_ascii=False)}")

    try:
        coll = get_collection()
        kwargs = {"profile_id": request.profile_id}
        if request.memory_info is not None:
            kwargs["memory_info"] = request.memory_info

        result = coll.update_profile(**kwargs)
        logger.info(f"【更新画像记忆】成功: {json.dumps(result, ensure_ascii=False, default=str)}")
        return result
    except VikingMemException as e:
        logger.error(f"【更新画像记忆】VikingMem 异常: {e.message}")
        raise HTTPException(status_code=500, detail=f"更新画像失败: {e.message}")
    except Exception as e:
        logger.error(f"【更新画像记忆】未知异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新画像失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    """健康检查"""
    try:
        get_collection()
        return {"status": "healthy", "vikingdb": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
