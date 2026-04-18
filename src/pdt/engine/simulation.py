"""
模拟引擎 — 管理角色、世界、事件、时间切片的通用沙盒核心

一个step()调用就是一个完整的切片循环：
  世界事件 + 自触发事件 → 感知过滤 → LLM生成 → 行为执行 → 事件广播 → tick
"""

import json
from pydantic import BaseModel, Field
from typing import Callable

from ..core.character import Character
from ..core.perception import PerceptionResult
from ..core.behavior import ActionType, JudgeResult, BehaviorChain
from ..core.spatial import WorldEvent
from ..core.timeslice import TimeSlice, Tempo
from ..core.event import Event, EventType, Valence, Duration
from ..core.vector import Dimension


# ============================================================
#  切片结果快照
# ============================================================

class SliceSnapshot(BaseModel):
    """单个切片的结果快照，用于前端展示和回放"""
    slice_index: int
    elapsed_label: str
    characters: dict[str, dict] = Field(default_factory=dict)
    # 每个角色: {"perception": ..., "behavior": ..., "position": ..., "body": ...}

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


# ============================================================
#  自触发规则
# ============================================================

class SelfTrigger(BaseModel):
    """
    维度组合达到阈值时自动生成内部事件。
    不需要外界刺激，角色自身就会产生内在体验。
    """
    name: str = Field(description="规则名")
    condition: Callable[["Character"], bool] = Field(
        description="触发条件：接收角色，返回是否触发"
    )
    event_content: str = Field(description="触发后生成的事件描述")
    intensity: float = Field(default=0.3, ge=0.0, le=1.0)
    valence: Valence = Field(default=Valence.POSITIVE)
    cooldown_slices: int = Field(default=3, description="冷却切片数，避免反复触发")
    last_triggered: dict[str, int] = Field(default_factory=dict, description="每个角色上次触发的切片号")

    class Config:
        arbitrary_types_allowed = True

    def check(self, character: Character, current_slice: int) -> Event | None:
        """检查是否触发，返回事件或None"""
        last = self.last_triggered.get(character.name, -999)
        if current_slice - last < self.cooldown_slices:
            return None
        if self.condition(character):
            self.last_triggered[character.name] = current_slice
            return Event(
                event_type=EventType.BODY,
                intensity=self.intensity,
                source="内在体验",
                content=self.event_content,
                valence=self.valence,
                duration=Duration.INSTANT,
            )
        return None


# ============================================================
#  内置自触发规则
# ============================================================

def _transcendence_trigger(char: Character) -> bool:
    """超越体验：高认知欲+高独立性+低依恋+低释放冲动"""
    curiosity = char.vector.get_value(Dimension.CURIOSITY)
    independence = char.vector.get_value(Dimension.INDEPENDENCE)
    attachment = char.vector.get_value(Dimension.ATTACHMENT)
    release = char.vector.get_value(Dimension.RELEASE_IMPULSE)
    return (curiosity > 0.6 and independence > 0.6
            and attachment < -0.2 and release < -0.2)


def _anxiety_trigger(char: Character) -> bool:
    """焦虑涌现：高情绪波动+低安全感+高释放冲动"""
    volatility = char.vector.get_value(Dimension.VOLATILITY)
    security = char.vector.get_value(Dimension.SECURITY)
    release = char.vector.get_value(Dimension.RELEASE_IMPULSE)
    return volatility > 0.6 and security < -0.4 and release > 0.4


def _loneliness_trigger(char: Character) -> bool:
    """孤独涌现：低亲和度+高依恋需求+低安全感"""
    affection = char.vector.get_value(Dimension.AFFECTION)
    attachment = char.vector.get_value(Dimension.ATTACHMENT)
    security = char.vector.get_value(Dimension.SECURITY)
    return affection < -0.3 and attachment > 0.4 and security < -0.2


BUILTIN_TRIGGERS = [
    SelfTrigger(
        name="超越体验",
        condition=_transcendence_trigger,
        event_content="一阵深深的平静感涌上来，仿佛与周围的一切融为一体",
        intensity=0.3,
        valence=Valence.POSITIVE,
        cooldown_slices=5,
    ),
    SelfTrigger(
        name="焦虑涌现",
        condition=_anxiety_trigger,
        event_content="一阵莫名的焦虑涌上来，心跳加速，无法集中注意力",
        intensity=0.4,
        valence=Valence.NEGATIVE,
        cooldown_slices=3,
    ),
    SelfTrigger(
        name="孤独涌现",
        condition=_loneliness_trigger,
        event_content="一种深深的孤独感突然袭来，渴望有人陪伴",
        intensity=0.3,
        valence=Valence.NEGATIVE,
        cooldown_slices=4,
    ),
]


# ============================================================
#  Simulation 核心类
# ============================================================

class Simulation:
    """
    通用模拟沙盒引擎

    用法:
        sim = Simulation(characters=[scholar, swordswoman])
        sim.set_scene_timeline(timeline)
        while sim.running:
            snapshot = sim.step()
            print(snapshot)
    """

    def __init__(
        self,
        characters: list[Character],
        tempo: Tempo = Tempo.NORMAL,
        behavior_generator=None,  # BehaviorGenerator，可选，None=纯数值模式
        judge_system=None,        # JudgeSystem，可选，None=自动创建
    ):
        self.characters = characters
        self.time_slice = TimeSlice(tempo=tempo)
        self.behavior_generator = behavior_generator
        self.running = True

        # 判定系统
        if judge_system is not None:
            self.judge_system = judge_system
        else:
            from .judge import JudgeSystem
            self.judge_system = JudgeSystem()

        # 世界事件队列：slice_index -> [WorldEvent]
        self.scene_timeline: dict[int, list[WorldEvent]] = {}
        # 持续事件（每轮都会出现的背景事件）
        self.sustained_events: list[WorldEvent] = []
        # 自触发规则
        self.self_triggers: list[SelfTrigger] = list(BUILTIN_TRIGGERS)
        # 历史快照
        self.history: list[SliceSnapshot] = []

        # 本切片的防御状态（每切片重置）
        self._defending_this_slice: dict[str, bool] = {}

    def _build_world_state(self) -> "WorldState":
        """从当前角色状态构建 WorldState"""
        from .judge import WorldState

        positions = {}
        facing = {}
        hp = {}
        dimensions = {}
        physique = {}
        defending = {}

        for char in self.characters:
            positions[char.name] = (char.position.x, char.position.y)
            facing[char.name] = (char.position.facing_x, char.position.facing_y)
            hp[char.name] = char.body.hp
            dimensions[char.name] = char.vector.to_list()
            defending[char.name] = self._defending_this_slice.get(char.name, False)
            # physique 由 get_physique 自动从 dimensions 推导

        scene = None
        # 如果有场景设置，附加
        if hasattr(self, '_scene') and self._scene:
            scene = self._scene

        return WorldState(
            scene=scene,
            character_positions=positions,
            character_facing=facing,
            character_hp=hp,
            character_dimensions=dimensions,
            character_defending=defending,
            slice_index=self.time_slice.slice_index,
        )

    def set_scene(self, scene) -> None:
        """设置当前场景"""
        self._scene = scene

    def set_scene_timeline(self, timeline: dict[int, list[WorldEvent]]) -> None:
        """设置场景时间线"""
        self.scene_timeline = timeline

    def add_sustained_event(self, event: WorldEvent) -> None:
        """添加持续事件（每轮都出现）"""
        self.sustained_events.append(event)

    def remove_sustained_event(self, event_content_substring: str) -> None:
        """移除持续事件"""
        self.sustained_events = [
            e for e in self.sustained_events
            if event_content_substring not in e.content
        ]

    def add_self_trigger(self, trigger: SelfTrigger) -> None:
        """添加自触发规则"""
        self.self_triggers.append(trigger)

    def inject_event(self, event: WorldEvent) -> None:
        """手动注入一个世界事件（立即生效）"""
        if self.time_slice.slice_index not in self.scene_timeline:
            self.scene_timeline[self.time_slice.slice_index] = []
        self.scene_timeline[self.time_slice.slice_index].append(event)

    def step(self) -> SliceSnapshot:
        """
        推进一个切片。返回快照。

        流程：
        1. 重置防御状态，收集世界事件 + 持续事件
        2. 构建 WorldState
        3. 每个角色：
           a. 自触发检查 → 维度影响
           b. 感知过滤
           c. LLM生成 BehaviorChain（或 ToolExecutor 旧路径）
           d. JudgeSystem 逐条判定 BehaviorChain
           e. 应用判定结果（位置、HP、事件广播）
        4. 时间推进
        """
        # 重置本切片防御状态
        self._defending_this_slice = {}

        snapshot = SliceSnapshot(
            slice_index=self.time_slice.slice_index,
            elapsed_label=self.time_slice.slice_label,
        )

        # 1. 收集世界事件
        world_events = list(self.scene_timeline.get(self.time_slice.slice_index, []))
        world_events.extend(self.sustained_events)

        # 2. 构建 WorldState
        ws = self._build_world_state()

        # 3. 每个角色
        for char in self.characters:
            # 3a. 自触发检查
            for trigger in self.self_triggers:
                internal_event = trigger.check(char, self.time_slice.slice_index)
                if internal_event:
                    char.process_event(internal_event)

            # 3b. 感知过滤
            perception = char.perceive(world_events)

            # 3c. 世界事件 → 维度影响
            for we in world_events:
                perceived = (
                    (we.event_type == "visual" and we.content in [e for e in perception.visual]) or
                    (we.event_type == "auditory" and any(we.content in e for e in perception.auditory)) or
                    (we.event_type == "tactile" and we.content in perception.tactile)
                )
                if not perceived:
                    continue
                try:
                    from ..core.event import EventType, Valence
                    evt_type = EventType(we.event_category)
                except ValueError:
                    evt_type = EventType.INFORMATION
                try:
                    valence = Valence(we.valence)
                except ValueError:
                    valence = Valence.NEUTRAL
                event = Event(
                    event_type=evt_type,
                    intensity=we.intensity,
                    source="world",
                    content=we.content,
                    valence=valence,
                    duration=Duration.INSTANT,
                )
                char.process_event(event)

            # 3d. 行为生成 + 判定
            tool_results: list = []
            judge_results: list = []

            if self.behavior_generator:
                # 新路径：LLM 生成 BehaviorChain → JudgeSystem 判定
                from ..core.behavior import BehaviorChain
                chain = self._generate_behavior_chain(char, perception)
                if chain and not chain.is_empty():
                    for action in chain.actions:
                        # 记录防御意图
                        if action.type == ActionType.DEFEND:
                            self._defending_this_slice[char.name] = True
                        # 更新 world_state 的 defending
                        ws.character_defending[char.name] = self._defending_this_slice.get(char.name, False)

                        jr = self.judge_system.judge(action, char.name, ws)
                        judge_results.append((action, jr))

                        # 应用判定结果到角色和世界
                        self._apply_judge_result(char, jr, ws, world_events)

                # 旧路径兼容：ToolExecutor（用于 speak/think/feel 等非判定工具）
                from ..engine.executor import ToolExecutor
                executor = ToolExecutor(self.characters)
                tool_results = self.behavior_generator.generate(
                    char, self.time_slice, perception, executor
                )

            # 3e. 收集工具调用产生的世界事件
            broadcast_events = []
            for tr in tool_results:
                for evt in tr.world_events:
                    world_events.append(WorldEvent(
                        content=evt["content"],
                        source_pos=char.position.pos_tuple(),
                        event_type=evt.get("event_type", "visual"),
                    ))
                    broadcast_events.append(evt)

            # 3f. 记录快照
            snapshot.characters[char.name] = {
                "perception": {
                    "visual": perception.visual,
                    "auditory": perception.auditory,
                    "tactile": perception.tactile,
                },
                "tool_results": [{"success": tr.success, "message": tr.message} for tr in tool_results],
                "judge_results": [
                    {"action": a.type.value, "success": jr.success,
                     "damage": jr.actual_damage, "desc": jr.broadcast_content,
                     "new_rule": jr.new_rule_id}
                    for a, jr in judge_results
                ],
                "position": {"x": char.position.x, "y": char.position.y,
                             "facing_x": char.position.facing_x, "facing_y": char.position.facing_y},
                "body": {"hp": char.body.hp, "heart_rate": char.body.heart_rate.value,
                         "impaired": [l.name for l in char.body.get_impaired_limbs()]},
                "goals": char.memory.short_term.short_term_goals,
                "drive_force": char.should_interrupt()[1],
                "drive_breakdown": {cat.value: val for cat, val in char.calculate_drives().items()},
            }

        # 4. 时间推进
        for char in self.characters:
            char.tick()
        self.time_slice = self.time_slice.advance()

        self.history.append(snapshot)
        return snapshot

    def _generate_behavior_chain(self, char: Character, perception) -> "BehaviorChain | None":
        """
        从角色当前状态生成 BehaviorChain

        目前先返回 None（让旧路径 ToolExecutor 处理 speak/think/feel），
        后续接入 LLM 行为生成器的 v4 版本直接输出 BehaviorChain。
        """
        # TODO: 接入 LLM v4 行为生成器
        # 当前阶段行为由 ToolExecutor 旧路径处理，判定由 JudgeSystem 接管物理效果
        return None

    def _apply_judge_result(
        self,
        char: Character,
        jr: JudgeResult,
        ws: "WorldState",
        world_events: list,
    ) -> None:
        """将判定结果应用到角色和世界"""
        # 位置更新
        if jr.actual_end_x is not None and jr.actual_end_y is not None:
            dx = jr.actual_end_x - char.position.x
            dy = jr.actual_end_y - char.position.y
            char.position.move(dx, dy)
        elif jr.actual_dx != 0 or jr.actual_dy != 0:
            char.position.move(jr.actual_dx, jr.actual_dy)

        # 伤害应用
        if jr.actual_damage > 0 and jr.target_name:
            from ..core.behavior import ActionType
            if jr.action_type == ActionType.ATTACK:
                # 找到目标角色
                for target_char in self.characters:
                    if target_char.name == jr.target_name:
                        target_char.body.deal_damage("chest", jr.actual_damage)
                        break

        # 广播事件
        if jr.broadcast_content:
            world_events.append(WorldEvent(
                content=jr.broadcast_content,
                source_pos=(char.position.x, char.position.y),
                event_type=jr.broadcast_type,
            ))

    def run(self, num_slices: int, callback: Callable[[SliceSnapshot], None] | None = None) -> list[SliceSnapshot]:
        """
        连续运行N个切片。
        callback在每个切片完成后调用，用于输出或展示。
        """
        results = []
        for _ in range(num_slices):
            snapshot = self.step()
            results.append(snapshot)
            if callback:
                callback(snapshot)
        return results

    def get_state_summary(self) -> dict:
        """获取当前所有角色的状态摘要"""
        return {
            "slice": self.time_slice.slice_index,
            "elapsed": self.time_slice.slice_label,
            "characters": {
                char.name: {
                    "position": char.position.pos_tuple(),
                    "hp": char.body.hp,
                    "drive_force": char.should_interrupt()[1],
                "drive_breakdown": {cat.value: val for cat, val in char.calculate_drives().items()},
                }
                for char in self.characters
            }
        }
