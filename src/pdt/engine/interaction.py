"""
双角色交互引擎

角色A输出行为 → 作为事件输入给角色B → 角色B反应 → 循环
支持打断机制：驱动力超过阈值时涌现打断行为
"""

from pydantic import BaseModel, Field
from ..core.character import Character
from ..core.event import Event, EventType, Valence, Duration
from .behavior import BehaviorGenerator


class InteractionStep(BaseModel):
    """一轮交互的结果"""
    round: int
    active_speaker: str
    action: dict  # behavior generator的输出
    vector_snapshot: dict[str, float]  # 当时的维度快照
    interrupt_happened: bool = False


class DualInteractionEngine(BaseModel):
    """双角色交互引擎"""
    
    character_a: Character
    character_b: Character
    behavior_generator: BehaviorGenerator | None = None
    max_rounds: int = Field(default=20, description="最大交互轮数")
    
    def _make_event_from_action(self, actor_name: str, action: dict, intensity: float = 0.5) -> Event:
        """将角色的行为转化为对方的事件输入"""
        speech = action.get("speech", "")
        act = action.get("action", "")
        content_parts = []
        if speech:
            content_parts.append(f"{actor_name}说: 「{speech}」")
        if act:
            content_parts.append(f"{actor_name}{act}")
        content = "。".join(content_parts) if content_parts else f"{actor_name}沉默"
        
        # 根据行为内容推断效价（简单启发式）
        valence = Valence.NEUTRAL
        negative_keywords = ["攻击", "怒", "骂", "杀", "打", "滚", "不", "拒绝", "推开", "威胁"]
        positive_keywords = ["帮", "谢", "好", "笑", "抱", "友", "善", "关心", "保护"]
        
        for kw in negative_keywords:
            if kw in content:
                valence = Valence.NEGATIVE
                break
        for kw in positive_keywords:
            if kw in content:
                valence = Valence.POSITIVE
                break
        
        return Event(
            event_type=EventType.INTERPERSONAL,
            intensity=intensity,
            source=actor_name,
            content=content,
            valence=valence,
            duration=Duration.INSTANT,
        )
    
    def run(self, initial_event: Event) -> list[InteractionStep]:
        """
        运行完整的双角色交互。
        initial_event: 触发交互的初始事件
        """
        results: list[InteractionStep] = []
        
        # 初始事件同时影响两个角色
        self.character_a.process_event(initial_event)
        self.character_b.process_event(initial_event)
        
        # 决定谁先反应（对事件的敏感度更高的人先说话）
        a_drive, _, _ = self.character_a.should_interrupt()
        b_drive, _, _ = self.character_b.should_interrupt()
        
        # 简单规则：释放冲动更高的人先说话
        a_release = self.character_a.vector.get_value(__import__(
            '..core.vector', fromlist=['Dimension']
        ).Dimension.RELEASE_IMPULSE)
        
        current_speaker = "A"
        current_char = self.character_a
        other_char = self.character_b
        listener = "B"
        
        last_action = None
        
        for round_num in range(1, self.max_rounds + 1):
            # 生成行为
            if self.behavior_generator and last_action:
                event_for_speaker = self._make_event_from_action(
                    listener, last_action
                )
                current_char.process_event(event_for_speaker)
                
                action = self.behavior_generator.generate_action(
                    current_char,
                    event_for_speaker,
                    other_action=last_action.get("speech", ""),
                )
            else:
                # 没有LLM时，用简化逻辑
                action = self._simple_action(current_char)
            
            # 快照
            snapshot = current_char.vector.summary()
            
            # 检查是否打断
            should_interrupt, _, _ = other_char.should_interrupt()
            
            step = InteractionStep(
                round=round_num,
                active_speaker=f"{current_char.name}({current_speaker})",
                action=action,
                vector_snapshot=snapshot,
                interrupt_happened=should_interrupt,
            )
            results.append(step)
            
            # 生成对方的事件
            event_for_other = self._make_event_from_action(
                current_char.name, action, intensity=initial_event.intensity * 0.8
            )
            other_char.process_event(event_for_other)
            
            # 时间推进
            self.character_a.tick()
            self.character_b.tick()
            
            # 决定下一轮谁说话
            # 如果听者的驱动力超过阈值，发生打断，下一轮听者变成说话者
            if should_interrupt:
                current_speaker, listener = listener, current_speaker
                current_char, other_char = other_char, current_char
            else:
                # 正常回合交替
                current_speaker, listener = listener, current_speaker
                current_char, other_char = other_char, current_char
            
            last_action = action
            
            # 简单终止条件：双方都沉默
            if not action.get("speech", "") and not action.get("action", ""):
                break
        
        return results
    
    def _simple_action(self, character: Character) -> dict:
        """没有LLM时的简化行为生成（纯数值驱动）"""
        from ..core.vector import Dimension
        
        speech = ""
        action = ""
        thought = ""
        emotion = "平静"
        
        # 基于维度值生成简化行为
        security = character.vector.get_value(Dimension.SECURITY)
        comfort = character.vector.get_value(Dimension.COMFORT)
        release = character.vector.get_value(Dimension.RELEASE_IMPULSE)
        empathy = character.vector.get_value(Dimension.EMPATHY)
        dominance = character.vector.get_value(Dimension.DOMINANCE)
        affection = character.vector.get_value(Dimension.AFFECTION)
        volatility = character.vector.get_value(Dimension.VOLATILITY)
        
        # 情绪推断
        if security < -0.3:
            emotion = "恐惧"
            action = "后退一步"
            thought = "不安全..."
        elif release > 0.4:
            emotion = "愤怒"
            action = "握紧拳头"
            thought = "忍不了了"
        elif comfort < -0.3:
            emotion = "烦躁"
            thought = "不舒服"
        elif empathy > 0.3 and affection > 0.3:
            emotion = "关切"
            speech = "你还好吗？"
            thought = "这人看起来不太好"
        
        # 目标推断
        satiation = character.vector.get_value(Dimension.SATIATION)
        goal = ""
        if satiation < -0.3:
            goal = "找吃的"
        elif security < -0.3:
            goal = "确保安全"
        elif character.memory.short_term.short_term_goals:
            goal = character.memory.short_term.short_term_goals[0]
        
        should_interrupt, force, _ = character.should_interrupt()
        
        return {
            "speech": speech,
            "action": action,
            "internal_thought": thought,
            "emotion": emotion,
            "target_goal": goal,
            "interrupting": should_interrupt,
        }
