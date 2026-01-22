"""
意识流处理模块：实现陪伴型智能机器狗的意识流架构

核心流程：
1. Emotion Grounding（情绪感受）
2. Evidence-Gated Recall（证据门控回忆）
3. Memory Verification（Viking 校验）
4. Response Synthesis（回复生成）
5. Memory Consolidation（记忆沉淀）
"""
import json
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from config import logger
from ai_utils import (
    emotion_grounding,
    subjective_recall,
    response_synthesis,
    memory_consolidation
)
from memory_utils import search_viking_memories


class ConsciousnessFlow:
    """
    意识流处理器
    
    实现一次完整的"意识流循环"，包含5个步骤
    """
    
    def __init__(
        self,
        user_id: str,
        dog_id: str,
        conversation_id: str,
        assistant_id: str = "assistant_001",
        model: str = "chatgpt"
    ):
        """
        初始化意识流处理器
        
        Args:
            user_id: 用户ID
            dog_id: 机器狗ID
            conversation_id: 对话ID
            assistant_id: 助手ID
            model: 使用的模型（chatgpt / deepseek）
        """
        self.user_id = user_id
        self.dog_id = dog_id
        self.conversation_id = conversation_id
        self.assistant_id = assistant_id
        self.model = model
        
        # 存储各步骤的结果
        self.emotion_state = None  # Step 1 结果
        self.subjective_recall = None  # Step 2 结果
        self.verified_recall = None  # Step 3 结果
        self.response = None  # Step 4 结果
        self.consolidation_result = None  # Step 5 结果
    
    def process(
        self,
        query: str,
        conversation_context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        执行完整的意识流处理流程
        
        Args:
            query: 用户输入
            conversation_context: 极短的会话上下文（1-2轮），禁止引入历史记忆
        
        Returns:
            包含所有步骤结果的字典
        """
        logger.info("=" * 80)
        logger.info("【意识流处理】开始")
        logger.info(f"用户输入: {query}")
        logger.info(f"用户ID: {self.user_id}, 狗ID: {self.dog_id}, 对话ID: {self.conversation_id}")
        
        # Step 0: 用户输入（已在参数中）
        # 禁止在此阶段引入历史记忆
        
        # Step 1: Emotion Grounding（情绪感受）
        logger.info("\n--- Step 1: Emotion Grounding（情绪感受）---")
        self.emotion_state = self._emotion_grounding(query, conversation_context)
        logger.info(f"情绪状态: {json.dumps(self.emotion_state, ensure_ascii=False)}")
        
        # Step 2: Evidence-Gated Recall（证据门控回忆）
        logger.info("\n--- Step 2: Evidence-Gated Recall（证据门控回忆）---")
        self.subjective_recall = self._evidence_gated_recall(query, conversation_context)
        logger.info(f"证据门控回忆: {json.dumps(self.subjective_recall, ensure_ascii=False)}")
        
        # Step 3: Memory Verification（Viking 校验）
        logger.info("\n--- Step 3: Memory Verification（Viking 校验）---")
        self.verified_recall = self._memory_verification()
        logger.info(f"验证后的回忆: {json.dumps(self.verified_recall, ensure_ascii=False)}")
        
        # Step 4: Response Synthesis（回复生成）
        logger.info("\n--- Step 4: Response Synthesis（回复生成）---")
        self.response = self._response_synthesis(query, conversation_context)
        logger.info(f"生成的回复: {self.response}")
        
        # Step 5: Memory Consolidation（记忆沉淀）
        logger.info("\n--- Step 5: Memory Consolidation（记忆沉淀）---")
        self.consolidation_result = self._memory_consolidation(query, self.response)
        logger.info(f"记忆沉淀结果: {json.dumps(self.consolidation_result, ensure_ascii=False)}")
        
        logger.info("\n【意识流处理】完成")
        logger.info("=" * 80)
        
        return {
            "emotion_state": self.emotion_state,
            "subjective_recall": self.subjective_recall,
            "verified_recall": self.verified_recall,
            "response": self.response,
            "consolidation_result": self.consolidation_result
        }
    
    def _emotion_grounding(
        self,
        query: str,
        conversation_context: Optional[List[Dict]]
    ) -> Dict:
        """
        Step 1: Emotion Grounding（情绪感受）
        
        让机器狗在"当下"形成一种情绪立场，而不是基于历史关系做判断。
        
        规则：
        - 使用模型：是
        - 是否查 Viking：否
        - 是否落库：否
        
        情绪只存在于本次请求生命周期，用于引导后续回忆。
        """
        try:
            emotion_result = emotion_grounding(
                query=query,
                conversation_context=conversation_context,
                model=self.model
            )
            return emotion_result
        except Exception as e:
            logger.error(f"【情绪感受】失败: {str(e)}")
            # 返回默认情绪状态
            return {
                "emotion": "neutral",
                "energy": "medium",
                "posture": "following",
                "confidence": 0.5
            }
    
    def _evidence_gated_recall(
        self,
        query: str,
        conversation_context: Optional[List[Dict]]
    ) -> Dict:
        """
        Step 2: Evidence-Gated Recall（证据门控回忆）
        
        核心原则：没有检索证据 → 不回忆，只承认不知道
        
        规则：
        - 使用模型：否（Step 2.1 判断）
        - 是否查 Viking：是（必须先查）
        - 是否落库：否
        
        流程：
        1. Step 2.1: 显式证据判断 - 根据检索结果判断状态
        2. Step 2.2: 不同状态，不同行为 - 返回相应的模板和规则
        
        状态说明：
        - NO_EVIDENCE: 零证据，禁止回忆，只允许澄清和承认不知道
        - WEAK_EVIDENCE: 弱证据，只能做条件化推断，必须使用不确定性语言
        - STRONG_EVIDENCE: 强证据，才允许回忆式表达，必须引用记忆来源
        """
        # 证据判断阈值（可根据需要调整）
        EVIDENCE_THRESHOLD = 0.6
        
        try:
            # Step 2.1: 显式证据判断 - 先查询记忆库
            logger.info("【证据门控回忆】Step 2.1: 查询记忆库")
            
            # 查询 conversation 库（事实来源）
            conv_memories, _ = search_viking_memories(
                query=query,
                user_id=self.user_id,
                assistant_id=self.dog_id,
                limit=5,
                collection_key="conversation"
            )
            
            # 查询 dog 库（关系记忆）
            dog_memories, _ = search_viking_memories(
                query=query,
                user_id=self.dog_id,
                assistant_id=self.assistant_id,
                limit=3,
                collection_key="dog"
            )
            
            # 查询 user 库（跨狗稳定事实）
            user_memories, _ = search_viking_memories(
                query=query,
                user_id=self.user_id,
                assistant_id=self.assistant_id,
                limit=3,
                collection_key="user"
            )
            
            # 合并所有检索到的记忆
            all_memories = conv_memories + dog_memories + user_memories
            
            # 判断状态
            memory_count = len(all_memories)
            max_score = max([mem.get("score", 0.0) for mem in all_memories], default=0.0)
            
            logger.info(f"【证据门控回忆】检索结果: count={memory_count}, max_score={max_score:.3f}, threshold={EVIDENCE_THRESHOLD}")
            
            # Step 2.1: 显式证据判断
            if memory_count == 0:
                recall_state = "NO_EVIDENCE"
            elif max_score < EVIDENCE_THRESHOLD:
                recall_state = "WEAK_EVIDENCE"
            else:
                recall_state = "STRONG_EVIDENCE"
            
            logger.info(f"【证据门控回忆】判断状态: {recall_state}")
            
            # Step 2.2: 不同状态，不同行为
            result = {
                "recall_state": recall_state,
                "retrieved_memories": all_memories,
                "memory_count": memory_count,
                "max_score": max_score,
                "threshold": EVIDENCE_THRESHOLD
            }
            
            if recall_state == "NO_EVIDENCE":
                # 零证据状态
                result.update({
                    "allowed_actions": [
                        "澄清型提问",
                        "当前问题的泛化建议",
                        "角色内的'我不确定'"
                    ],
                    "prohibited_actions": [
                        "禁止回忆",
                        "禁止补全",
                        "禁止'我记得你以前......'"
                    ],
                    "response_template": "我现在没有关于你这个问题的具体记忆，我们可以从现在开始一起建立。"
                })
            elif recall_state == "WEAK_EVIDENCE":
                # 弱证据状态
                result.update({
                    "allowed_actions": [
                        "只能做条件化推断",
                        "必须使用不确定性语言"
                    ],
                    "response_template": "我不完全确定，但从之前的零散记录来看，可能是......如果不对你可以纠正我。",
                    "top_memories": all_memories[:3]  # 取前3条作为参考
                })
            else:  # STRONG_EVIDENCE
                # 强证据状态
                result.update({
                    "allowed_actions": [
                        "才允许'回忆式表达'",
                        "必须引用记忆来源"
                    ],
                    "response_template": "之前你在 xx 时间提到过 xx，所以我猜你现在是在问这个。",
                    "top_memories": [mem for mem in all_memories if mem.get("score", 0.0) >= EVIDENCE_THRESHOLD][:3]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"【证据门控回忆】失败: {str(e)}")
            # 失败时返回 NO_EVIDENCE 状态
            return {
                "recall_state": "NO_EVIDENCE",
                "retrieved_memories": [],
                "memory_count": 0,
                "max_score": 0.0,
                "threshold": EVIDENCE_THRESHOLD,
                "allowed_actions": [
                    "澄清型提问",
                    "当前问题的泛化建议",
                    "角色内的'我不确定'"
                ],
                "prohibited_actions": [
                    "禁止回忆",
                    "禁止补全",
                    "禁止'我记得你以前......'"
                ],
                "response_template": "我现在没有关于你这个问题的具体记忆，我们可以从现在开始一起建立。",
                "error": str(e)
            }
    
    def _memory_verification(self) -> Dict:
        """
        Step 3: Memory Verification（Viking 校验）
        
        由于 Step 2 已经完成证据门控回忆并查询了记忆库，Step 3 主要进行结果整理和分类。
        
        规则：
        - 使用模型：否
        - 是否查 Viking：否（已在 Step 2 查询）
        - 是否落库：否
        
        功能：
        - 整理 Step 2 检索到的记忆
        - 按类型分类（conversation/dog/user）
        - 为 Step 4 回复生成提供结构化数据
        """
        if not self.subjective_recall:
            return {
                "recall_state": "NO_EVIDENCE",
                "verified_fragments": [],
                "decayed_fragments": [],
                "supporting_conversations": [],
                "supporting_memories": []
            }
        
        try:
            # 从 Step 2 的结果中获取信息
            recall_state = self.subjective_recall.get("recall_state", "NO_EVIDENCE")
            all_memories = self.subjective_recall.get("retrieved_memories", [])
            
            # 按 collection_key 分类记忆（需要从记忆项中提取，如果没有则按顺序分配）
            # 由于 search_viking_memories 返回的记忆可能没有明确的 collection_key 标记
            # 这里我们按 memory_type 和来源进行分类
            supporting_conversations = []
            supporting_memories = []
            
            for mem in all_memories:
                memory_type = mem.get("memory_type", "")
                # event_v1 通常是 conversation，profile_v1 通常是 dog/user
                if memory_type == "event_v1":
                    supporting_conversations.append(mem)
                else:
                    supporting_memories.append(mem)
            
            # 根据 recall_state 决定哪些记忆可以使用
            if recall_state == "NO_EVIDENCE":
                verified_fragments = []
                decayed_fragments = []
            elif recall_state == "WEAK_EVIDENCE":
                # 弱证据：所有记忆都标记为需要谨慎使用
                verified_fragments = []
                decayed_fragments = all_memories  # 标记为需要衰减
            else:  # STRONG_EVIDENCE
                # 强证据：高分的记忆可以验证使用
                threshold = self.subjective_recall.get("threshold", 0.6)
                verified_fragments = [mem for mem in all_memories if mem.get("score", 0.0) >= threshold]
                decayed_fragments = [mem for mem in all_memories if mem.get("score", 0.0) < threshold]
            
            return {
                "recall_state": recall_state,
                "verified_fragments": verified_fragments,
                "decayed_fragments": decayed_fragments,
                "supporting_conversations": supporting_conversations[:3],  # 最多3条
                "supporting_memories": supporting_memories[:3]  # 最多3条
            }
            
        except Exception as e:
            logger.error(f"【Viking校验】失败: {str(e)}")
            # 校验失败时，返回默认状态
            return {
                "recall_state": "NO_EVIDENCE",
                "verified_fragments": [],
                "decayed_fragments": [],
                "supporting_conversations": [],
                "supporting_memories": []
            }
    
    def _response_synthesis(
        self,
        query: str,
        conversation_context: Optional[List[Dict]]
    ) -> str:
        """
        Step 4: Response Synthesis（回复生成）
        
        生成自然、带有边界感的回复。
        
        规则：
        - 使用模型：是
        - 是否查 Viking：否
        - 是否落库：否
        
        模型允许承认模糊、承认遗忘、请求补充。
        """
        try:
            response = response_synthesis(
                query=query,
                conversation_context=conversation_context,
                emotion_state=self.emotion_state,
                verified_recall=self.verified_recall,
                model=self.model
            )
            return response
        except Exception as e:
            logger.error(f"【回复生成】失败: {str(e)}")
            return "抱歉，我现在有些困惑，能再说一遍吗？"
    
    def _memory_consolidation(
        self,
        query: str,
        answer: str
    ) -> Dict:
        """
        Step 5: Memory Consolidation（记忆沉淀）
        
        将**被反复验证、对关系产生实质影响的痕迹**写入长期记忆。
        
        规则：
        - 使用模型：可选（用于总结）
        - 是否查 Viking：否
        - 是否落库：是
        
        写入位置：dog 记忆库（以 user 为 key）
        写入内容：稳定态度变化、明确的长期偏好、被多次想起并验证的互动痕迹
        
        不写入的内容：
        - 单次情绪
        - 模糊回忆
        - 未经验证的判断
        """
        try:
            # 只有被验证的回忆才参与记忆沉淀
            verified_fragments = self.verified_recall.get("verified_fragments", [])
            
            if not verified_fragments:
                logger.info("【记忆沉淀】没有可沉淀的验证回忆，跳过")
                return {
                    "should_write": False,
                    "reason": "没有可沉淀的验证回忆"
                }
            
            # 调用记忆沉淀函数
            consolidation_result = memory_consolidation(
                query=query,
                answer=answer,
                verified_fragments=verified_fragments,
                user_id=self.user_id,
                dog_id=self.dog_id,
                model=self.model
            )
            
            return consolidation_result
            
        except Exception as e:
            logger.error(f"【记忆沉淀】失败: {str(e)}")
            return {
                "should_write": False,
                "reason": f"记忆沉淀失败: {str(e)}"
            }
    
    def _extract_recall_query_text(self) -> str:
        """
        从主观回忆中提取用于Viking查询的关键文本
        """
        if not self.subjective_recall:
            return ""
        
        fragments = self.subjective_recall.get("recall_fragments", [])
        impressions = self.subjective_recall.get("long_term_impressions", [])
        
        # 合并所有回忆文本
        all_texts = []
        for frag in fragments:
            if isinstance(frag, str):
                all_texts.append(frag)
            elif isinstance(frag, dict):
                all_texts.append(str(frag.get("content", "")))
        
        for imp in impressions:
            if isinstance(imp, str):
                all_texts.append(imp)
            elif isinstance(imp, dict):
                all_texts.append(str(imp.get("content", "")))
        
        # 取前200字符作为查询文本
        query_text = " ".join(all_texts)[:200]
        return query_text
