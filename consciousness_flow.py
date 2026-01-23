"""
意识流处理模块：实现陪伴型智能机器狗的意识流架构

新流程：
1. 用户输入
2. 情绪感知（隐式，不存）
3. 【状态机枢纽】
   - 当前状态评估
   - 状态跃迁
   - 行为约束生成
4. 主观回忆生成（受状态影响）
5. Viking 验证 / 补充
6. 回忆稳定 or 衰减（受状态影响）
7. 行为生成（语言 + 行为）
8. 记忆反馈筛选
9. 仅将"被验证、被反复想起的痕迹"写入 dog
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
from memory_utils import search_viking_memories, extract_user_nickname
from state_machine import StateMachine


class ConsciousnessFlow:
    """
    意识流处理器
    
    实现一次完整的"意识流循环"，按照新流程执行
    """
    
    def __init__(
        self,
        user_id: str,
        dog_id: str,
        conversation_id: str,
        assistant_id: str = "assistant_001",
        model: str = "chatgpt",
        state_machine: Optional[StateMachine] = None
    ):
        """
        初始化意识流处理器
        
        Args:
            user_id: 用户ID
            dog_id: 机器狗ID
            conversation_id: 对话ID
            assistant_id: 助手ID
            model: 使用的模型（chatgpt / deepseek）
            state_machine: 状态机实例（如果为None，则创建新实例）
        """
        self.user_id = user_id
        self.dog_id = dog_id
        self.conversation_id = conversation_id
        self.assistant_id = assistant_id
        self.model = model
        
        # 初始化状态机
        if state_machine is None:
            self.state_machine = StateMachine()
        else:
            self.state_machine = state_machine
        
        # 存储各步骤的结果
        self.emotion_perception = None  # Step 2: 情绪感知（隐式，不存）
        self.current_states = None  # Step 3: 当前状态
        self.behavior_constraints = None  # Step 3: 行为约束
        self.subjective_recall = None  # Step 4: 主观回忆生成
        self.verified_recall = None  # Step 5: Viking 验证/补充
        self.stable_recall = None  # Step 6: 稳定回忆
        self.decayed_recall = None  # Step 6: 衰减回忆
        self.response = None  # Step 7: 行为生成（语言）
        self.behavior_actions = None  # Step 7: 行为生成（行为）
        self.memory_feedback = None  # Step 8: 记忆反馈筛选
        self.dog_memory_write = None  # Step 9: 写入dog的记忆
    
    def process(
        self,
        query: str,
        conversation_context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        执行完整的意识流处理流程（新流程）
        
        Args:
            query: 用户输入
            conversation_context: 极短的会话上下文（1-2轮），禁止引入历史记忆
        
        Returns:
            包含所有步骤结果的字典
        """
        logger.info("=" * 80)
        logger.info("【意识流处理】开始（新流程）")
        logger.info(f"用户输入: {query}")
        logger.info(f"用户ID: {self.user_id}, 狗ID: {self.dog_id}, 对话ID: {self.conversation_id}")
        
        # Step 1: 用户输入（已在参数中）
        # 禁止在此阶段引入历史记忆
        
        # Step 2: 情绪感知（隐式，不存）
        logger.info("\n--- Step 2: 情绪感知（隐式，不存）---")
        self.emotion_perception = self._emotion_perception(query, conversation_context)
        logger.info(f"情绪感知: {json.dumps(self.emotion_perception, ensure_ascii=False)}")
        
        # Step 3: 【状态机枢纽】
        logger.info("\n--- Step 3: 【状态机枢纽】---")
        self.current_states = self.state_machine.evaluate_current_state()
        logger.info(f"当前状态评估: {json.dumps(self.current_states, ensure_ascii=False, indent=2)}")
        
        # 状态跃迁
        interaction_context = {
            "query": query,
            "conversation_context": conversation_context,
            "sentiment": self.emotion_perception.get("sentiment", "neutral") if self.emotion_perception else "neutral"
        }
        self.current_states = self.state_machine.transition(
            emotion_perception=self.emotion_perception,
            interaction_context=interaction_context
        )
        logger.info(f"状态跃迁后: {json.dumps(self.current_states, ensure_ascii=False, indent=2)}")
        
        # 行为约束生成
        self.behavior_constraints = self.state_machine.generate_behavior_constraints()
        logger.info(f"行为约束: {json.dumps(self.behavior_constraints, ensure_ascii=False, indent=2)}")
        
        # Step 4: 主观回忆生成（受状态影响）
        logger.info("\n--- Step 4: 主观回忆生成（受状态影响）---")
        self.subjective_recall = self._subjective_recall_with_state(
            query, conversation_context, self.behavior_constraints
        )
        logger.info(f"主观回忆: {json.dumps(self.subjective_recall, ensure_ascii=False)}")
        
        # Step 5: Viking 验证 / 补充
        logger.info("\n--- Step 5: Viking 验证 / 补充---")
        self.verified_recall = self._viking_verification_and_supplement()
        logger.info(f"验证后的回忆: {json.dumps(self.verified_recall, ensure_ascii=False)}")
        
        # Step 6: 回忆稳定 or 衰减（受状态影响）
        logger.info("\n--- Step 6: 回忆稳定 or 衰减（受状态影响）---")
        self.stable_recall, self.decayed_recall = self._recall_stabilization_and_decay()
        logger.info(f"稳定回忆: {len(self.stable_recall) if self.stable_recall else 0} 条")
        logger.info(f"衰减回忆: {len(self.decayed_recall) if self.decayed_recall else 0} 条")
        
        # Step 7: 行为生成（语言 + 行为）
        logger.info("\n--- Step 7: 行为生成（语言 + 行为）---")
        self.response, self.behavior_actions = self._behavior_generation(query, conversation_context)
        logger.info(f"生成的回复: {self.response}")
        logger.info(f"行为动作: {json.dumps(self.behavior_actions, ensure_ascii=False)}")
        
        # Step 8: 记忆反馈筛选
        logger.info("\n--- Step 8: 记忆反馈筛选---")
        self.memory_feedback = self._memory_feedback_filtering(query, self.response)
        logger.info(f"记忆反馈筛选结果: {json.dumps(self.memory_feedback, ensure_ascii=False)}")
        
        # Step 9: 仅将"被验证、被反复想起的痕迹"写入 dog
        logger.info("\n--- Step 9: 写入 dog 记忆---")
        self.dog_memory_write = self._write_verified_traces_to_dog()
        logger.info(f"写入 dog 记忆结果: {json.dumps(self.dog_memory_write, ensure_ascii=False)}")
        
        logger.info("\n【意识流处理】完成")
        logger.info("=" * 80)
        
        return {
            "emotion_perception": self.emotion_perception,
            "current_states": self.current_states,
            "behavior_constraints": self.behavior_constraints,
            "subjective_recall": self.subjective_recall,
            "verified_recall": self.verified_recall,
            "stable_recall": self.stable_recall,
            "decayed_recall": self.decayed_recall,
            "response": self.response,
            "behavior_actions": self.behavior_actions,
            "memory_feedback": self.memory_feedback,
            "dog_memory_write": self.dog_memory_write
        }
    
    def _emotion_perception(
        self,
        query: str,
        conversation_context: Optional[List[Dict]]
    ) -> Dict:
        """
        Step 2: 情绪感知（隐式，不存）
        
        让机器狗在"当下"感知用户情绪，但不存储。
        
        规则：
        - 使用模型：是
        - 是否查 Viking：否
        - 是否落库：否
        
        情绪感知只存在于本次请求生命周期，用于引导状态机跃迁和后续回忆。
        """
        try:
            emotion_result = emotion_grounding(
                query=query,
                conversation_context=conversation_context,
                model=self.model
            )
            # 转换为更简洁的格式，不存储
            return {
                "sentiment": emotion_result.get("emotion", "neutral"),
                "energy": emotion_result.get("energy", "medium"),
                "intensity": emotion_result.get("confidence", 0.5)
            }
        except Exception as e:
            logger.error(f"【情绪感知】失败: {str(e)}")
            # 返回默认情绪感知
            return {
                "sentiment": "neutral",
                "energy": "medium",
                "intensity": 0.5
            }
    
    def _subjective_recall_with_state(
        self,
        query: str,
        conversation_context: Optional[List[Dict]],
        behavior_constraints: Dict
    ) -> Dict:
        """
        Step 4: 主观回忆生成（受状态影响）
        
        根据当前状态和行为约束，生成主观回忆。
        
        规则：
        - 使用模型：是（受状态影响）
        - 是否查 Viking：是（必须先查）
        - 是否落库：否
        
        回忆生成受状态影响：
        - 情绪状态影响回忆偏向（正面/负面/中性）
        - 电量状态影响回忆活跃度
        - 性格状态影响回忆风格
        """
        # 证据判断阈值（可根据需要调整）
        EVIDENCE_THRESHOLD = 0.6
        
        try:
            # 先查询记忆库
            logger.info("【主观回忆生成】查询记忆库")
            
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
            
            logger.info(f"【主观回忆生成】检索结果: count={memory_count}, max_score={max_score:.3f}, threshold={EVIDENCE_THRESHOLD}")
            
            # 根据状态影响回忆生成
            recall_bias = behavior_constraints.get("recall_bias", "neutral")
            memory_stability = behavior_constraints.get("memory_stability", "medium")
            
            # 根据回忆偏向过滤记忆
            if recall_bias == "positive":
                # 偏向正面回忆
                filtered_memories = [m for m in all_memories if m.get("score", 0.0) > 0.5]
            elif recall_bias == "negative":
                # 偏向负面回忆（如果有）
                filtered_memories = all_memories
            else:
                # 中性，不过滤
                filtered_memories = all_memories
            
            # 判断状态
            if memory_count == 0:
                recall_state = "NO_EVIDENCE"
            elif max_score < EVIDENCE_THRESHOLD:
                recall_state = "WEAK_EVIDENCE"
            else:
                recall_state = "STRONG_EVIDENCE"
            
            logger.info(f"【主观回忆生成】状态: {recall_state}, 回忆偏向: {recall_bias}, 记忆稳定性: {memory_stability}")
            
            # 使用模型生成主观回忆（受状态影响）
            try:
                subjective_recall_text = subjective_recall(
                    query=query,
                    conversation_context=conversation_context,
                    retrieved_memories=filtered_memories,
                    behavior_constraints=behavior_constraints,
                    model=self.model,
                    user_id=self.user_id,
                    dog_id=self.dog_id,
                    assistant_id=self.assistant_id
                )
            except Exception as e:
                logger.warning(f"【主观回忆生成】模型生成失败: {str(e)}")
                subjective_recall_text = ""
            
            result = {
                "recall_state": recall_state,
                "retrieved_memories": filtered_memories,
                "memory_count": memory_count,
                "max_score": max_score,
                "threshold": EVIDENCE_THRESHOLD,
                "recall_bias": recall_bias,
                "memory_stability": memory_stability,
                "subjective_recall_text": subjective_recall_text
            }
            
            return result
            
        except Exception as e:
            logger.error(f"【主观回忆生成】失败: {str(e)}")
            return {
                "recall_state": "NO_EVIDENCE",
                "retrieved_memories": [],
                "memory_count": 0,
                "max_score": 0.0,
                "threshold": EVIDENCE_THRESHOLD,
                "recall_bias": "neutral",
                "memory_stability": "medium",
                "subjective_recall_text": "",
                "error": str(e)
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
    
    def _viking_verification_and_supplement(self) -> Dict:
        """
        Step 5: Viking 验证 / 补充
        
        对主观回忆进行验证和补充。
        
        规则：
        - 使用模型：可选（用于补充）
        - 是否查 Viking：是（验证）
        - 是否落库：否
        
        功能：
        - 验证主观回忆的准确性
        - 补充缺失的信息
        - 标记已验证和未验证的回忆片段
        """
        if not self.subjective_recall:
            return {
                "recall_state": "NO_EVIDENCE",
                "verified_fragments": [],
                "unverified_fragments": [],
                "supplemented_fragments": [],
                "supporting_conversations": [],
                "supporting_memories": []
            }
        
        try:
            # 从 Step 4 的结果中获取信息
            recall_state = self.subjective_recall.get("recall_state", "NO_EVIDENCE")
            all_memories = self.subjective_recall.get("retrieved_memories", [])
            subjective_recall_text = self.subjective_recall.get("subjective_recall_text", "")
            
            # 按 memory_type 分类记忆
            supporting_conversations = []
            supporting_memories = []
            
            for mem in all_memories:
                memory_type = mem.get("memory_type", "")
                if memory_type == "event_v1":
                    supporting_conversations.append(mem)
                else:
                    supporting_memories.append(mem)
            
            # 根据 recall_state 和记忆分数决定验证结果
            threshold = self.subjective_recall.get("threshold", 0.6)
            
            if recall_state == "NO_EVIDENCE":
                verified_fragments = []
                unverified_fragments = []
                supplemented_fragments = []
            elif recall_state == "WEAK_EVIDENCE":
                # 弱证据：标记为未验证，需要补充
                verified_fragments = []
                unverified_fragments = all_memories
                supplemented_fragments = []  # 可以在这里调用模型补充
            else:  # STRONG_EVIDENCE
                # 强证据：高分的记忆可以验证
                verified_fragments = [mem for mem in all_memories if mem.get("score", 0.0) >= threshold]
                unverified_fragments = [mem for mem in all_memories if mem.get("score", 0.0) < threshold]
                supplemented_fragments = []  # 可以基于主观回忆文本补充
            
            return {
                "recall_state": recall_state,
                "verified_fragments": verified_fragments,
                "unverified_fragments": unverified_fragments,
                "supplemented_fragments": supplemented_fragments,
                "subjective_recall_text": subjective_recall_text,
                "supporting_conversations": supporting_conversations[:3],
                "supporting_memories": supporting_memories[:3]
            }
            
        except Exception as e:
            logger.error(f"【Viking验证/补充】失败: {str(e)}")
            return {
                "recall_state": "NO_EVIDENCE",
                "verified_fragments": [],
                "unverified_fragments": [],
                "supplemented_fragments": [],
                "supporting_conversations": [],
                "supporting_memories": []
            }
    
    def _recall_stabilization_and_decay(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Step 6: 回忆稳定 or 衰减（受状态影响）
        
        根据当前状态决定哪些回忆稳定，哪些衰减。
        
        规则：
        - 使用模型：否
        - 是否查 Viking：否
        - 是否落库：否
        
        状态影响：
        - memory_stability 影响稳定/衰减的判断
        - 高稳定性：更多回忆稳定
        - 低稳定性：更多回忆衰减
        """
        if not self.verified_recall:
            return [], []
        
        try:
            verified_fragments = self.verified_recall.get("verified_fragments", [])
            unverified_fragments = self.verified_recall.get("unverified_fragments", [])
            
            # 获取当前状态的记忆稳定性
            memory_stability = self.behavior_constraints.get("memory_stability", "medium") if self.behavior_constraints else "medium"
            
            # 根据稳定性决定稳定和衰减的回忆
            stable_recall = []
            decayed_recall = []
            
            if memory_stability == "very_high":
                # 非常高的稳定性：所有验证的回忆都稳定
                stable_recall = verified_fragments
                decayed_recall = unverified_fragments
            elif memory_stability == "high":
                # 高稳定性：高分验证的回忆稳定
                stable_recall = [m for m in verified_fragments if m.get("score", 0.0) >= 0.7]
                decayed_recall = [m for m in verified_fragments if m.get("score", 0.0) < 0.7] + unverified_fragments
            elif memory_stability == "medium":
                # 中等稳定性：中等分验证的回忆稳定
                stable_recall = [m for m in verified_fragments if m.get("score", 0.0) >= 0.6]
                decayed_recall = [m for m in verified_fragments if m.get("score", 0.0) < 0.6] + unverified_fragments
            else:  # low
                # 低稳定性：大部分回忆衰减
                stable_recall = [m for m in verified_fragments if m.get("score", 0.0) >= 0.8]
                decayed_recall = [m for m in verified_fragments if m.get("score", 0.0) < 0.8] + unverified_fragments
            
            logger.info(f"【回忆稳定/衰减】稳定性: {memory_stability}, 稳定: {len(stable_recall)}, 衰减: {len(decayed_recall)}")
            
            return stable_recall, decayed_recall
            
        except Exception as e:
            logger.error(f"【回忆稳定/衰减】失败: {str(e)}")
            return [], []
    
    def _behavior_generation(
        self,
        query: str,
        conversation_context: Optional[List[Dict]]
    ) -> Tuple[str, Dict]:
        """
        Step 7: 行为生成（语言 + 行为）
        
        根据当前状态和回忆生成语言回复和行为动作。
        
        规则：
        - 使用模型：是
        - 是否查 Viking：否
        - 是否落库：否
        """
        try:
            # 从记忆中提取用户名字
            user_nickname = None
            try:
                # 直接查询user库获取用户名字（更可靠）
                user_memories, _ = search_viking_memories(
                    query="用户名字",
                    user_id=self.user_id,
                    assistant_id=self.assistant_id,
                    limit=3,
                    collection_key="user",
                    extra_filter={"memory_type": ["profile_v1"]}
                )
                
                if user_memories:
                    user_nickname = extract_user_nickname(user_memories)
                    if user_nickname and user_nickname != "朋友":
                        logger.info(f"【行为生成】提取到用户名字: {user_nickname}")
                    else:
                        logger.info("【行为生成】未找到用户名字，使用默认称呼")
                        user_nickname = None
                else:
                    logger.info("【行为生成】user库中没有找到相关记忆")
            except Exception as e:
                logger.warning(f"【行为生成】提取用户名字失败: {str(e)}")
            
            # 生成语言回复
            response = response_synthesis(
                query=query,
                conversation_context=conversation_context,
                emotion_state=self.emotion_perception,
                verified_recall=self.verified_recall,
                stable_recall=self.stable_recall,
                behavior_constraints=self.behavior_constraints,
                user_nickname=user_nickname,
                model=self.model
            )
            
            # 生成行为动作（根据状态和行为约束）
            behavior_actions = self._generate_behavior_actions()
            
            return response, behavior_actions
            
        except Exception as e:
            logger.error(f"【行为生成】失败: {str(e)}")
            return "抱歉，我现在有些困惑，能再说一遍吗？", {}
    
    def _generate_behavior_actions(self) -> Dict:
        """生成行为动作"""
        if not self.behavior_constraints:
            return {}
        
        actions = {
            "activity_level": self.behavior_constraints.get("activity_level", "medium"),
            "response_speed": self.behavior_constraints.get("response_speed", "normal"),
            "interaction_capacity": self.behavior_constraints.get("interaction_capacity", "medium")
        }
        
        # 根据状态生成具体动作
        emotion_state = self.current_states.get("emotion", {}) if self.current_states else {}
        emotion_name = emotion_state.get("name", "平静")
        
        if emotion_name == "开心" or emotion_name == "兴奋":
            actions["tail_wagging"] = "high"
            actions["body_movement"] = "active"
        elif emotion_name == "疲惫":
            actions["tail_wagging"] = "low"
            actions["body_movement"] = "minimal"
        else:
            actions["tail_wagging"] = "medium"
            actions["body_movement"] = "normal"
        
        return actions
    
    def _memory_feedback_filtering(self, query: str, response: str) -> Dict:
        """
        Step 8: 记忆反馈筛选
        
        筛选哪些记忆被反复想起、被验证，值得写入。
        
        规则：
        - 使用模型：可选（用于判断）
        - 是否查 Viking：否
        - 是否落库：否
        """
        try:
            # 统计稳定回忆中被反复想起的
            if not self.stable_recall:
                return {
                    "repeatedly_recalled": [],
                    "verified_traces": [],
                    "should_write_count": 0
                }
            
            # 简单实现：高分且稳定的回忆被认为是反复想起的
            repeatedly_recalled = [
                m for m in self.stable_recall 
                if m.get("score", 0.0) >= 0.7
            ]
            
            # 被验证的痕迹
            verified_traces = [
                m for m in repeatedly_recalled
                if m.get("memory_type") in ["profile_v1", "event_v1"]
            ]
            
            return {
                "repeatedly_recalled": repeatedly_recalled,
                "verified_traces": verified_traces,
                "should_write_count": len(verified_traces)
            }
            
        except Exception as e:
            logger.error(f"【记忆反馈筛选】失败: {str(e)}")
            return {
                "repeatedly_recalled": [],
                "verified_traces": [],
                "should_write_count": 0
            }
    
    def _write_verified_traces_to_dog(self) -> Dict:
        """
        Step 9: 仅将"被验证、被反复想起的痕迹"写入 dog
        
        规则：
        - 使用模型：可选（用于总结）
        - 是否查 Viking：否
        - 是否落库：是（只写入dog库）
        """
        try:
            if not self.memory_feedback:
                return {
                    "should_write": False,
                    "reason": "没有记忆反馈"
                }
            
            verified_traces = self.memory_feedback.get("verified_traces", [])
            
            if not verified_traces:
                logger.info("【写入dog记忆】没有可写入的验证痕迹，跳过")
                return {
                    "should_write": False,
                    "reason": "没有可写入的验证痕迹"
                }
            
            # 调用记忆沉淀函数，只写入dog库
            from memory_writing import consolidate_memory_to_dog
            
            # 合并所有验证痕迹的文本
            memory_texts = []
            for trace in verified_traces:
                content = trace.get("content", "")
                if content:
                    memory_texts.append(content)
            
            if not memory_texts:
                return {
                    "should_write": False,
                    "reason": "验证痕迹没有有效内容"
                }
            
            # 合并文本
            combined_memory = "\n".join(memory_texts[:3])  # 最多3条
            
            # 写入dog库
            result = consolidate_memory_to_dog(
                user_id=self.user_id,
                dog_id=self.dog_id,
                memory_text=combined_memory,
                assistant_id=self.assistant_id
            )
            
            return {
                "should_write": True,
                "written_count": len(verified_traces),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"【写入dog记忆】失败: {str(e)}")
            return {
                "should_write": False,
                "reason": f"写入失败: {str(e)}"
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
