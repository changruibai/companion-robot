"""
状态机模块：实现多维度状态管理、状态评估、状态跃迁和行为约束生成

核心功能：
1. 当前状态评估
2. 状态跃迁
3. 行为约束生成
"""
import json
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from config import logger


class StateMachine:
    """
    多维度状态机
    
    管理机器狗的多维度状态（性格、情绪、技能、电量、品种等），
    并根据交互情况实现状态跃迁和行为约束生成。
    """
    
    def __init__(self, config_path: str = "state_machine_config.json"):
        """
        初始化状态机
        
        Args:
            config_path: 状态机配置文件路径
        """
        self.config = self._load_config(config_path)
        self.current_states = self._initialize_states()
        self.state_history = []  # 记录状态变化历史
        
    def _load_config(self, config_path: str) -> Dict:
        """加载状态机配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"【状态机】配置文件加载成功: {config_path}")
            return config
        except Exception as e:
            logger.error(f"【状态机】配置文件加载失败: {str(e)}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "dimensions": {},
            "global_transition_factors": {},
            "behavior_synthesis_rules": {}
        }
    
    def _initialize_states(self) -> Dict[str, Dict]:
        """
        初始化所有维度的状态
        
        Returns:
            当前状态字典，格式：{dimension_name: {state_id, value, ...}}
        """
        states = {}
        dimensions = self.config.get("dimensions", {})
        
        for dim_name, dim_config in dimensions.items():
            default_state_id = dim_config.get("default_state")
            states_list = dim_config.get("states", [])
            
            # 找到默认状态
            default_state = None
            for state in states_list:
                if state.get("id") == default_state_id:
                    default_state = state
                    break
            
            if default_state:
                states[dim_name] = {
                    "state_id": default_state_id,
                    "value": default_state.get("value", 0.5),
                    "name": default_state.get("name", ""),
                    "description": default_state.get("description", ""),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # 如果没有找到默认状态，使用第一个状态
                if states_list:
                    first_state = states_list[0]
                    states[dim_name] = {
                        "state_id": first_state.get("id", ""),
                        "value": first_state.get("value", 0.5),
                        "name": first_state.get("name", ""),
                        "description": first_state.get("description", ""),
                        "timestamp": datetime.now().isoformat()
                    }
        
        logger.info(f"【状态机】状态初始化完成: {json.dumps(states, ensure_ascii=False, indent=2)}")
        return states
    
    def evaluate_current_state(self) -> Dict[str, Dict]:
        """
        评估当前状态
        
        Returns:
            当前所有维度的状态
        """
        logger.info("【状态机】评估当前状态")
        return self.current_states.copy()
    
    def transition(
        self,
        emotion_perception: Optional[Dict] = None,
        interaction_context: Optional[Dict] = None
    ) -> Dict[str, Dict]:
        """
        执行状态跃迁
        
        Args:
            emotion_perception: 情绪感知结果（隐式，不存储）
            interaction_context: 交互上下文（用户输入、对话历史等）
        
        Returns:
            跃迁后的状态
        """
        logger.info("【状态机】开始状态跃迁")
        
        # 记录跃迁前的状态
        previous_states = self.current_states.copy()
        
        # 对每个维度进行状态跃迁评估
        dimensions = self.config.get("dimensions", {})
        
        for dim_name, dim_config in dimensions.items():
            current_state_id = self.current_states[dim_name]["state_id"]
            current_state_config = self._get_state_config(dim_name, current_state_id)
            
            if not current_state_config:
                continue
            
            # 获取该状态的跃迁规则
            transition_rules = current_state_config.get("transition_rules", {})
            
            # 评估每个可能的跃迁
            for target_state_id, rule in transition_rules.items():
                condition = rule.get("condition", "")
                probability = rule.get("probability", 0.0)
                
                # 评估跃迁条件
                should_transition = self._evaluate_transition_condition(
                    condition,
                    emotion_perception,
                    interaction_context,
                    dim_name
                )
                
                if should_transition:
                    # 根据概率决定是否跃迁
                    import random
                    if random.random() < probability:
                        # 执行跃迁
                        target_state_config = self._get_state_config(dim_name, target_state_id)
                        if target_state_config:
                            self.current_states[dim_name] = {
                                "state_id": target_state_id,
                                "value": target_state_config.get("value", 0.5),
                                "name": target_state_config.get("name", ""),
                                "description": target_state_config.get("description", ""),
                                "timestamp": datetime.now().isoformat(),
                                "transitioned_from": current_state_id
                            }
                            
                            logger.info(
                                f"【状态机】{dim_name} 状态跃迁: {current_state_id} -> {target_state_id}"
                            )
                            break
        
        # 应用全局跃迁因子（如时间衰减）
        self._apply_global_transition_factors(interaction_context)
        
        # 记录状态变化历史
        if previous_states != self.current_states:
            self.state_history.append({
                "timestamp": datetime.now().isoformat(),
                "previous": previous_states,
                "current": self.current_states.copy()
            })
        
        return self.current_states.copy()
    
    def _get_state_config(self, dimension_name: str, state_id: str) -> Optional[Dict]:
        """获取指定维度和状态的配置"""
        dimensions = self.config.get("dimensions", {})
        dim_config = dimensions.get(dimension_name, {})
        states_list = dim_config.get("states", [])
        
        for state in states_list:
            if state.get("id") == state_id:
                return state
        return None
    
    def _evaluate_transition_condition(
        self,
        condition: str,
        emotion_perception: Optional[Dict],
        interaction_context: Optional[Dict],
        dimension_name: str
    ) -> bool:
        """
        评估跃迁条件
        
        Args:
            condition: 条件表达式（如 "energy < 0.3"）
            emotion_perception: 情绪感知结果
            interaction_context: 交互上下文
        
        Returns:
            是否满足条件
        """
        if not condition:
            return False
        
        try:
            # 简单的条件评估（可以根据需要扩展）
            # 这里实现一些常见的条件判断
            
            # 从情绪感知中获取能量值
            if "energy" in condition:
                energy = emotion_perception.get("energy", 0.5) if emotion_perception else 0.5
                if "<" in condition:
                    threshold = float(condition.split("<")[1].strip())
                    return energy < threshold
                elif ">" in condition:
                    threshold = float(condition.split(">")[1].strip())
                    return energy > threshold
            
            # 从交互上下文中获取信息
            if "positive_interaction" in condition:
                return interaction_context.get("sentiment", "neutral") == "positive" if interaction_context else False
            
            if "new_topic_detected" in condition:
                return interaction_context.get("is_new_topic", False) if interaction_context else False
            
            if "complex_question" in condition:
                return interaction_context.get("is_complex", False) if interaction_context else False
            
            if "positive_feedback" in condition:
                return interaction_context.get("has_positive_feedback", False) if interaction_context else False
            
            if "rest_period" in condition:
                # 检查是否有休息期（可以通过时间间隔判断）
                return interaction_context.get("is_rest_period", False) if interaction_context else False
            
            if "time_decay" in condition:
                # 时间衰减（简化处理）
                return True  # 可以根据实际时间间隔计算
            
            if "learning_events" in condition:
                # 学习事件数量
                learning_count = interaction_context.get("learning_events", 0) if interaction_context else 0
                if ">" in condition:
                    threshold = int(condition.split(">")[1].strip())
                    return learning_count > threshold
            
            if "success_rate" in condition:
                success_rate = interaction_context.get("success_rate", 0.0) if interaction_context else 0.0
                if ">" in condition:
                    threshold = float(condition.split(">")[1].strip())
                    return success_rate > threshold
            
            if "error_rate" in condition:
                error_rate = interaction_context.get("error_rate", 0.0) if interaction_context else 0.0
                if ">" in condition:
                    threshold = float(condition.split(">")[1].strip())
                    return error_rate > threshold
            
            if "high_activity" in condition:
                return interaction_context.get("is_high_activity", False) if interaction_context else False
            
            # 默认返回False
            return False
            
        except Exception as e:
            logger.error(f"【状态机】条件评估失败: {condition}, 错误: {str(e)}")
            return False
    
    def _apply_global_transition_factors(self, interaction_context: Optional[Dict]):
        """应用全局跃迁因子（如时间衰减）"""
        global_factors = self.config.get("global_transition_factors", {})
        
        # 时间衰减（简化处理，实际可以根据时间间隔计算）
        time_decay = global_factors.get("time_decay", {})
        decay_rate = time_decay.get("rate", 0.01)
        
        # 对某些维度应用时间衰减（如电量）
        if "battery" in self.current_states:
            current_value = self.current_states["battery"]["value"]
            new_value = max(0.0, current_value - decay_rate)
            self.current_states["battery"]["value"] = new_value
            
            # 如果电量降到阈值以下，可能需要状态跃迁
            if new_value < 0.3 and self.current_states["battery"]["state_id"] != "low":
                # 可以触发到低电量的跃迁
                pass
    
    def generate_behavior_constraints(self) -> Dict[str, Any]:
        """
        生成行为约束
        
        根据当前所有维度的状态，生成综合的行为约束，
        用于指导后续的回忆生成、行为生成等。
        
        Returns:
            行为约束字典
        """
        logger.info("【状态机】生成行为约束")
        
        constraints = {
            "language_style": [],
            "response_length": "medium",
            "emoji_usage": "medium",
            "interaction_frequency": "medium",
            "recall_bias": "neutral",
            "memory_stability": "medium",
            "response_tone": "neutral",
            "response_confidence": "medium",
            "activity_level": "medium",
            "response_speed": "normal",
            "interaction_capacity": "medium"
        }
        
        # 收集所有维度的行为约束
        for dim_name, state_info in self.current_states.items():
            state_id = state_info["state_id"]
            state_config = self._get_state_config(dim_name, state_id)
            
            if not state_config:
                continue
            
            behavior_constraints = state_config.get("behavior_constraints", {})
            
            # 合并约束（优先级：情绪 > 性格 > 电量 > 其他）
            if dim_name == "emotion":
                # 情绪约束优先级最高
                if "recall_bias" in behavior_constraints:
                    constraints["recall_bias"] = behavior_constraints["recall_bias"]
                if "memory_stability" in behavior_constraints:
                    constraints["memory_stability"] = behavior_constraints["memory_stability"]
                if "response_tone" in behavior_constraints:
                    constraints["response_tone"] = behavior_constraints["response_tone"]
            
            if dim_name == "personality":
                if "language_style" in behavior_constraints:
                    constraints["language_style"].append(behavior_constraints["language_style"])
                if "response_length" in behavior_constraints:
                    constraints["response_length"] = behavior_constraints["response_length"]
                if "emoji_usage" in behavior_constraints:
                    constraints["emoji_usage"] = behavior_constraints["emoji_usage"]
                if "interaction_frequency" in behavior_constraints:
                    constraints["interaction_frequency"] = behavior_constraints["interaction_frequency"]
            
            if dim_name == "battery":
                if "activity_level" in behavior_constraints:
                    constraints["activity_level"] = behavior_constraints["activity_level"]
                if "response_speed" in behavior_constraints:
                    constraints["response_speed"] = behavior_constraints["response_speed"]
                if "interaction_capacity" in behavior_constraints:
                    constraints["interaction_capacity"] = behavior_constraints["interaction_capacity"]
            
            if dim_name == "skill":
                if "response_confidence" in behavior_constraints:
                    constraints["response_confidence"] = behavior_constraints["response_confidence"]
        
        # 处理语言风格列表
        if constraints["language_style"]:
            constraints["language_style"] = ", ".join(constraints["language_style"])
        else:
            constraints["language_style"] = "自然、友好"
        
        logger.info(f"【状态机】行为约束生成完成: {json.dumps(constraints, ensure_ascii=False, indent=2)}")
        return constraints
    
    def get_state_summary(self) -> Dict:
        """
        获取状态摘要
        
        Returns:
            状态摘要字典
        """
        summary = {
            "current_states": self.current_states,
            "state_count": len(self.current_states),
            "recent_transitions": self.state_history[-5:] if len(self.state_history) > 5 else self.state_history
        }
        return summary
