"""
AI 工具模块：OpenAI/DeepSeek 调用、回答生成、记忆决策等
"""
import json
import re
import time
import logging
from typing import List, Optional, Dict
from openai import OpenAI
from config import (
    OPENAI_API_KEY, DEEPSEEK_API_KEY, VIKINGDB_PROFILE_TYPE,
    logger
)
from memory_utils import extract_dog_info, extract_user_nickname

# ==================== AI 客户端初始化 ====================

# OpenAI 客户端
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# DeepSeek 客户端（可选）
deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    logger.info("DeepSeek 客户端初始化成功")
else:
    logger.warning("未设置 DEEPSEEK_API_KEY，DeepSeek 模型将不可用")


# ==================== 回答生成 ====================

def generate_answer_with_ai(query: str, memories: List[dict]) -> str:
    """
    使用 OpenAI 整合记忆库知识生成回答
    
    Args:
        query: 用户问题
        memories: 相关记忆列表
    
    Returns:
        AI 生成的回答
    """
    logger.info("【AI生成回答】开始")
    logger.info(f"用户问题: {query}")
    logger.info(f"使用的记忆数量: {len(memories)}")
    
    # 构建上下文
    context_parts = []
    if memories:
        context_parts.append("=== 相关记忆库信息（这些是关于当前用户的信息）===")
        for i, mem in enumerate(memories, 1):
            memory_type = mem.get('memory_type', '')
            memory_type_desc = ''
            if memory_type == 'profile_v1':
                memory_type_desc = '（用户画像）'
            elif memory_type == 'event_v1':
                memory_type_desc = '（历史对话/事件）'
            context_parts.append(f"\n记忆 {i}{memory_type_desc} (相关性: {mem.get('score', 0):.2f}):")
            context_parts.append(mem.get('content', ''))
    
    context = "\n".join(context_parts) if context_parts else "暂无相关记忆库信息。"
    
    # 构建提示词
    system_prompt = """你是一个智能助手，能够基于用户的记忆库信息回答问题。
请仔细阅读和分析提供的记忆库信息，这些记忆都是关于当前用户的信息。特别注意：
1. **仔细分析记忆内容**：如果记忆中有用户的名字（如"张三"、"李四"等）、个人信息、偏好等，请直接使用这些信息回答
2. **不要忽略细节**：记忆中的任何信息都可能与问题相关，比如"张三喜欢咖啡"中的"张三"就是用户的名字
3. **直接回答**：如果记忆中有相关信息，要明确指出并引用，不要说自己"没有找到"相关信息
4. **优先使用记忆**：如果记忆库信息与问题相关，优先使用记忆库中的信息，不要绕弯子
5. **只有在确实没有相关信息时**，才可以说没有找到，并可以基于通用知识回答
6. 回答要自然、友好、准确，直接回答用户的问题"""
    
    user_prompt = f"""用户问题：{query}

{context}

请仔细分析以上记忆库信息。这些记忆都是关于当前用户的信息。如果记忆中有直接相关的信息（如名字、个人信息等），请直接使用这些信息回答用户的问题。回答要自然、友好、准确。"""
    
    # 记录请求参数
    request_params = {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 500,
    }
    logger.info(f"【AI生成回答】请求参数: {json.dumps(request_params, ensure_ascii=False, indent=2)}")
    
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
        
        answer = response.choices[0].message.content
        logger.info("【AI生成回答】成功")
        logger.info(f"生成的回答: {answer}")
        logger.info(
            f"响应元数据: 模型={response.model}, "
            f"使用tokens={response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}"
        )
        
        return answer
    except Exception as e:
        error_msg = f"AI 服务暂时不可用: {str(e)}"
        logger.error(f"【AI生成回答】调用失败: {str(e)}")
        logger.error(f"错误详情: {json.dumps({'error': str(e), 'type': type(e).__name__}, ensure_ascii=False)}")
        return error_msg


def generate_answer_with_dog_persona(
    query: str,
    user_memories: List[dict],
    dog_memories: List[dict],
    relationship_memories: List[dict],
    conversation_memories: List[dict],
    model: str = "chatgpt"
) -> str:
    """
    按照机器狗角色模板生成回答，支持选择不同的模型（chatgpt / deepseek）
    
    Args:
        query: 用户问题
        user_memories: 用户记忆列表
        dog_memories: 狗的记忆列表
        relationship_memories: 关系记忆列表
        conversation_memories: 对话记忆列表
        model: 使用的模型（chatgpt / deepseek）
    
    Returns:
        机器狗角色的回答
    """
    logger.info(f"【机器狗回答生成】开始，使用模型: {model}")
    logger.info(f"用户问题: {query}")
    
    # 提取狗的信息
    dog_info = extract_dog_info(dog_memories)
    dog_name = dog_info["name"]
    dog_character = dog_info["character"]
    dog_tone = dog_info["tone"]
    
    # 提取用户昵称
    user_nickname = extract_user_nickname(user_memories)
    
    # 组织关系记忆
    relationship_summary = _organize_relationship_memories(relationship_memories)
    
    # 组织对话记忆（最近的2条）
    conversation_items = _organize_memories(conversation_memories, max_items=2, max_len=80)
    if not conversation_items:
        conversation_items = ["你们刚刚开始对话"]
    
    # 组织用户记忆（最多2条）
    user_memory_items = _organize_memories(user_memories, max_items=2, max_len=80)
    if not user_memory_items:
        user_memory_items = ["你对这个人的了解还在建立中"]
    
    # 组织狗的记忆（最多1条）
    dog_memory_items = _organize_memories(dog_memories, max_items=1, max_len=80)
    if not dog_memory_items:
        dog_memory_items = ["你正在学习和成长"]
    
    # 构建模板化的提示词
    system_prompt = """你是一只陪伴型机器狗，需要以真实、自然的方式与用户对话。
你的回答要：
- 情绪真实，体现机器狗的性格特点
- 不重复旧话，每次回答都要有新意
- 不暴露记忆来源，自然地融入对话中
- 基于提供的记忆信息，但要用自己的话表达
- 保持角色一致性，始终以机器狗的身份说话"""
    
    user_prompt = f"""【你的身份】
你是一只陪伴型机器狗，名字是 {dog_name}。
你的性格是：{dog_character}
你的说话风格是：{dog_tone}

【你和这个人的长期关系】
你和 {user_nickname} 已经相处了一段时间，你们的关系特点是：
- {relationship_summary}

【你们当前阶段的共同记忆】
{chr(10).join([f"- {item}" for item in conversation_items])}

【关于这个人】
你对他的长期了解包括：
{chr(10).join([f"- {item}" for item in user_memory_items])}

【你自己的成长】
{chr(10).join([f"- {item}" for item in dog_memory_items])}

【当前对话】
用户：{query}

请你以陪伴型机器狗的身份回应：
- 情绪真实
- 不重复旧话
- 不暴露记忆来源"""
    
    # 根据模型选择客户端和模型名称
    if model == "deepseek":
        if not deepseek_client:
            error_msg = "抱歉，DeepSeek 服务未配置，请设置 DEEPSEEK_API_KEY 环境变量"
            logger.error(error_msg)
            return error_msg
        client = deepseek_client
        model_name = "deepseek-chat"
    else:  # 默认使用 chatgpt
        client = openai_client
        model_name = "gpt-4o-mini"
    
    # 记录请求参数
    request_params = {
        "model": model_name,
        "temperature": 0.8,
        "max_tokens": 500,
    }
    logger.info(f"【机器狗回答生成】请求参数: {json.dumps(request_params, ensure_ascii=False, indent=2)}")
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        logger.info(f"【机器狗回答生成】成功（{model.upper()}）")
        logger.info(f"生成的回答: {answer}")
        return answer
    except Exception as e:
        error_msg = f"抱歉，AI 服务暂时不可用: {str(e)}"
        logger.error(f"【机器狗回答生成】调用失败（{model.upper()}）: {str(e)}")
        return error_msg


def _organize_relationship_memories(relationship_memories: List[dict]) -> str:
    """组织关系记忆摘要"""
    if relationship_memories:
        rel_contents = [mem.get('content', '') for mem in relationship_memories[:3] if mem.get('content')]
        if rel_contents:
            summary_text = "；".join([c[:100] + "..." if len(c) > 100 else c for c in rel_contents])
            return summary_text
    return "你们建立了良好的陪伴关系"


def _organize_memories(memories: List[dict], max_items: int = 5, max_len: int = 80) -> List[str]:
    """组织记忆列表，截取指定长度"""
    items = []
    for mem in memories[:max_items]:
        content = mem.get('content', '')
        if content:
            short_content = content[:max_len] + "..." if len(content) > max_len else content
            items.append(short_content)
    return items


# ==================== 记忆写入决策 ====================

def decide_memory_writing(
    user_id: str,
    dog_id: str,
    conversation_id: str,
    query: str,
    answer: str,
    user_memories: List[dict],
    dog_memories: List[dict],
    relationship_memories: List[dict],
    conversation_memories: List[dict],
    model: str = "chatgpt",
) -> Optional[dict]:
    """
    使用 LLM 做「记忆写入决策」
    
    需要判断：
    - 是否写入（should_write）
    - 是否涉及情绪变化（has_emotion_change）
    - 是否是关系转折（is_relationship_turning）
    - 是否是重复信息（is_duplicate）
    - 写入到哪里（targets：user / dog / relationship / conversation）
    
    Args:
        user_id: 用户ID
        dog_id: 狗ID
        conversation_id: 对话ID
        query: 用户问题
        answer: 机器狗回答
        user_memories: 用户记忆列表
        dog_memories: 狗的记忆列表
        relationship_memories: 关系记忆列表
        conversation_memories: 对话记忆列表
        model: 使用的模型（chatgpt / deepseek）
    
    Returns:
        决策结果字典，包含 should_write, targets, memories 等字段
        如果决策失败则返回 None
    """
    system_prompt = """你是一个"记忆写入决策器"，负责为陪伴型机器狗系统判断是否需要把本轮对话写入长期记忆。
你必须严格按照下面的语义做结构化判断：
1. should_write：本轮是否值得写入任意一种记忆（true/false）。
2. has_emotion_change：本轮是否出现用户情绪的明显变化，例如从开心到低落、从平静到愤怒等（true/false）。
3. is_relationship_turning：本轮是否出现关系上的明显里程碑或转折（例如第一次见面、确定长期陪伴、发生争执又和好等）（true/false）。
4. is_duplicate：如果本轮表达的信息与历史记忆高度重复、没有新增有效信息，则为 true；否则为 false。
5. targets：需要写入的记忆类型列表，可选值为 ["user", "dog", "relationship", "conversation"]。
   - 当发现用户的稳定偏好、身份信息、长期习惯等 → 归类为 "user"。
   - 当出现你和用户关系的重要节点或阶段性总结 → 归类为 "relationship"。
   - 当出现本轮强烈情绪、关键事件、一次性的细节 → 归类为 "conversation"。
   - 当是机器狗自身设定或认知的变化（比如"以后我要更主动地提醒你运动"）→ 归类为 "dog"。
6. memories：对每个需要写入的 target，给出一段适合落库的中文摘要文本。
   - 要用第三人称或中性描述，而不是"我猜你……"之类的主观猜测。
   - 要避免口头语，适合后续直接拼接进提示词使用。
7. reason：用 1-2 句话说明你做出该决策的原因，便于人类调试。

请只输出一个 JSON 对象，不要包含其它说明文字。"""

    def _shorten(mem_list: List[dict], max_items: int = 5, max_len: int = 80) -> List[str]:
        items = []
        for mem in mem_list[:max_items]:
            c = str(mem.get("content", "")).strip()
            if not c:
                continue
            if len(c) > max_len:
                c = c[:max_len] + "..."
            items.append(c)
        return items

    user_ctx = _shorten(user_memories)
    dog_ctx = _shorten(dog_memories)
    rel_ctx = _shorten(relationship_memories)
    conv_ctx = _shorten(conversation_memories)

    user_prompt = f"""【身份信息】
user_id = {user_id}
dog_id = {dog_id}
conversation_id = {conversation_id}

【本轮用户输入】
{query}

【本轮机器狗回复】
{answer}

【相关历史记忆摘要】
- user 相关（用户长期特征）:
{chr(10).join(["  - " + x for x in user_ctx]) or "  - （暂无）"}

- dog 相关（机器狗设定或认知）:
{chr(10).join(["  - " + x for x in dog_ctx]) or "  - （暂无）"}

- relationship 相关（关系里程碑）:
{chr(10).join(["  - " + x for x in rel_ctx]) or "  - （暂无）"}

- conversation 相关（历史情绪 / 事件）:
{chr(10).join(["  - " + x for x in conv_ctx]) or "  - （暂无）"}

请根据以上信息做出记忆写入决策，并按系统提示返回 JSON。"""

    # 根据模型选择客户端和模型名称
    if model == "deepseek":
        if not deepseek_client:
            logger.warning("【记忆写入决策】DeepSeek 服务未配置，跳过写入逻辑")
            return None
        client = deepseek_client
        model_name = "deepseek-chat"
    else:  # 默认使用 chatgpt
        client = openai_client
        model_name = "gpt-4o-mini"
    
    try:
        # 设置超时时间为 30 秒，并增加重试逻辑
        max_retries = 2
        retry_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=400,
                    timeout=30.0,
                )
                break  # 成功则跳出重试循环
            except Exception as retry_error:
                if attempt < max_retries:
                    logger.warning(
                        f"【记忆写入决策】第 {attempt + 1} 次尝试失败: {str(retry_error)}，"
                        f"{retry_delay}秒后重试..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    raise retry_error  # 最后一次重试失败，抛出异常
        
        # 检查响应结构
        if not resp or not resp.choices or len(resp.choices) == 0:
            logger.warning("【记忆写入决策】API 响应为空或 choices 为空")
            return None
        
        content = (resp.choices[0].message.content or "").strip()
        logger.info(f"【记忆写入决策】AI 原始输出: {content}")
        
        # 检查 content 是否为空
        if not content:
            logger.warning("【记忆写入决策】AI 返回内容为空，无法解析 JSON")
            return None
        
        # 尝试提取 JSON（可能包含 markdown 代码块）
        try:
            # 如果内容被 markdown 代码块包裹，先提取 JSON 部分
            if content.startswith("```"):
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1).strip()
                else:
                    # 尝试提取第一个 { 到最后一个 } 之间的内容
                    start_idx = content.find('{')
                    end_idx = content.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        content = content[start_idx:end_idx+1]
            
            data = json.loads(content)
        except json.JSONDecodeError as json_error:
            logger.error(f"【记忆写入决策】JSON 解析失败: {str(json_error)}")
            logger.error(f"【记忆写入决策】原始内容: {content[:200]}...")
            return None
        
        if not isinstance(data, dict):
            logger.error(f"【记忆写入决策】解析结果不是字典类型: {type(data)}")
            return None
        
        # 基础字段兜底
        data.setdefault("should_write", False)
        data.setdefault("has_emotion_change", False)
        data.setdefault("is_relationship_turning", False)
        data.setdefault("is_duplicate", False)
        data.setdefault("targets", [])
        data.setdefault("memories", {})
        
        logger.info(f"【记忆写入决策】决策完成: should_write={data.get('should_write')}, targets={data.get('targets')}")
        return data
    except Exception as e:
        logger.error(f"【记忆写入决策】调用失败，跳过写入逻辑: {str(e)}")
        return None


# ==================== 画像提取 ====================

def extract_profile_info_with_ai(
    query: str,
    answer: str,
    old_profile: Optional[str]
) -> Optional[dict]:
    """
    从本轮对话中提取画像信息，返回 memory_info（dict）
    
    Args:
        query: 用户问题
        answer: 助手回答
        old_profile: 旧画像文本
    
    Returns:
        memory_info 字典（包含 user_profile），如果没有可提取的信息则返回 None
    """
    system_prompt = """你是一个从多轮对话中维护用户画像的助手。
你会拿到"旧画像文本"和"本轮对话（用户提问与助手回复）"：
1. 如果本轮没有出现任何新的或冲突的画像信息，返回：{"has_new": false}.
2. 如果有新的或需要修改的画像信息，请在保留旧画像中未被改变信息的前提下，生成一份"更新后的完整画像文本"：
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
        logger.error(f"【画像提取】失败，跳过本轮更新: {str(e)}")
        return None


def summarize_profile_with_ai(
    old_profile: Optional[str],
    new_profile: str,
    model: str = "chatgpt"
) -> Optional[str]:
    """
    将历史画像和新画像交给AI进行总结，生成一个合并后的完整画像
    
    Args:
        old_profile: 历史画像文本（可能为None）
        new_profile: 新理解的画像文本
        model: 使用的模型（chatgpt / deepseek）
    
    Returns:
        总结后的画像文本，如果失败则返回None
    """
    logger.info("【画像总结】开始")
    logger.info(f"历史画像: {old_profile or '（无历史画像）'}")
    logger.info(f"新画像: {new_profile}")
    
    system_prompt = """你是一个用户画像维护助手，负责将历史画像和新画像进行智能合并和总结。
你的任务是：
1. 仔细分析历史画像和新画像中的所有信息
2. 合并重复信息，保留所有有价值的内容
3. 对于冲突的信息（如名字、年龄等），以新画像为准
4. 生成一份完整、准确、简洁的用户画像文本
5. 画像应该用中文描述，可以是若干条目或自然段
6. 确保画像信息完整，不丢失重要细节

请直接输出合并后的画像文本，不要包含其他说明文字。"""
    
    user_prompt = f"""【历史画像】:
{old_profile or "（无历史画像）"}

【新理解的画像】:
{new_profile}

请将以上两个画像进行智能合并和总结，生成一份完整、准确的用户画像。"""
    
    # 根据模型选择客户端和模型名称
    if model == "deepseek":
        if not deepseek_client:
            logger.warning("【画像总结】DeepSeek 服务未配置，使用 ChatGPT")
            client = openai_client
            model_name = "gpt-4o-mini"
        else:
            client = deepseek_client
            model_name = "deepseek-chat"
    else:  # 默认使用 chatgpt
        client = openai_client
        model_name = "gpt-4o-mini"
    
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        content = resp.choices[0].message.content.strip()
        logger.info(f"【画像总结】AI 原始输出: {content}")
        
        if not content or not content.strip():
            logger.warning("【画像总结】AI 返回内容为空")
            return None
        
        summarized_profile = content.strip()
        logger.info(f"【画像总结】成功: {summarized_profile[:200]}...")
        return summarized_profile
    except Exception as e:
        logger.error(f"【画像总结】失败: {str(e)}")
        return None
