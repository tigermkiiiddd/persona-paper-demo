"""
持续行为系统 — 角色输出事件链，世界逐条判定

行为不是瞬时的，是一个事件链（BehaviorChain）：
  move(target_x=12, target_y=10, speed=5, duration=0.6)
  → attack(target="黑衣人", damage=8, weapon_range=2, duration=0.4)

世界对每条 action 独立判定，返回实际结果。
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Literal


# ============================================================
#  Action 类型枚举
# ============================================================

class ActionType(str, Enum):
    MOVE = "move"               # 移动到目标位置
    ATTACK = "attack"           # 攻击目标角色
    INTERACT = "interact"       # 与场景物体交互
    SOCIAL = "social"           # 社交行为（说话/表情/姿态）
    USE_ITEM = "use_item"       # 使用物品
    WAIT = "wait"               # 等待/待命
    FLEE = "flee"               # 逃跑
    DEFEND = "defend"           # 防御姿态
    CUSTOM = "custom"           # 自定义（需要天道判定）


# ============================================================
#  单条 Action
# ============================================================

class BehaviorAction(BaseModel):
    """事件链中的单个持续行为"""
    type: ActionType = Field(description="行为类型")

    # 时间线
    start_tick: float = Field(default=0.0, ge=0.0, description="事件链内的起始偏移（分钟）")
    duration: float = Field(default=1.0, ge=0.0, description="持续时长（分钟）")

    # ---- move ----
    target_x: Optional[float] = Field(default=None, description="移动目标X（格）")
    target_y: Optional[float] = Field(default=None, description="移动目标Y（格）")
    speed: float = Field(default=5.0, ge=0.0, description="移动速度（格/分钟）")

    # ---- attack ----
    target_name: Optional[str] = Field(default=None, description="目标角色名")
    damage: float = Field(default=0.0, ge=0.0, description="基础伤害（HP/分钟）")
    weapon_range: float = Field(default=1.5, ge=0.0, description="武器攻击范围（格）")

    # ---- interact ----
    object_id: Optional[str] = Field(default=None, description="交互物体ID")
    interact_type: Optional[str] = Field(default=None, description="交互类型: open/pickup/use/break/...")

    # ---- social ----
    speech_content: Optional[str] = Field(default=None, description="说话内容")
    speech_volume: str = Field(default="normal", description="音量: whisper/normal/loud/shout")
    gesture: Optional[str] = Field(default=None, description="肢体语言描述")

    # ---- use_item ----
    item_name: Optional[str] = Field(default=None, description="使用物品名")
    item_target: Optional[str] = Field(default=None, description="物品作用目标")

    # ---- flee ----
    flee_direction_x: Optional[float] = Field(default=None, description="逃跑方向X")
    flee_direction_y: Optional[float] = Field(default=None, description="逃跑方向Y")

    # ---- defend ----
    defend_against: Optional[str] = Field(default=None, description="防御目标角色")

    # ---- custom ----
    custom_description: Optional[str] = Field(default=None, description="自定义行为描述（需要天道判定）")

    # 通用
    description: str = Field(default="", description="行为的自然语言描述")

    @property
    def end_tick(self) -> float:
        return self.start_tick + self.duration


# ============================================================
#  判定结果
# ============================================================

class JudgeResult(BaseModel):
    """单条 action 的判定结果"""
    action_type: ActionType = Field(description="行为类型")
    success: bool = Field(default=True, description="是否成功")
    reason: str = Field(default="", description="失败原因")

    # 实际效果
    actual_dx: float = Field(default=0.0, description="实际X位移（格）")
    actual_dy: float = Field(default=0.0, description="实际Y位移（格）")
    actual_damage: float = Field(default=0.0, description="实际造成的伤害")
    actual_end_x: Optional[float] = Field(default=None, description="实际到达位置X")
    actual_end_y: Optional[float] = Field(default=None, description="实际到达位置Y")

    # 世界事件（广播给其他角色）
    broadcast_content: str = Field(default="", description="广播给其他角色的事件描述")
    broadcast_type: str = Field(default="visual", description="广播事件类型: visual/auditory/tactile")
    broadcast_valence: str = Field(default="neutral", description="广播事件效价")

    # 生成的新法则（天道介入时）
    new_rule_id: Optional[str] = Field(default=None, description="天道新生成的法则ID（如有）")


# ============================================================
#  事件链
# ============================================================

class BehaviorChain(BaseModel):
    """角色在一个切片内的事件链"""
    actions: list[BehaviorAction] = Field(default_factory=list, description="按顺序执行的行为列表")

    @property
    def total_duration(self) -> float:
        if not self.actions:
            return 0.0
        return max(a.end_tick for a in self.actions)

    def is_empty(self) -> bool:
        return len(self.actions) == 0


# ============================================================
#  切片结果（改造后的 SliceSnapshot）
# ============================================================

class ActionReplay(BaseModel):
    """单个 action 的回放数据（前端动画用）"""
    action_type: ActionType
    start_tick: float
    duration: float
    success: bool
    reason: str = ""

    # 动画用
    start_pos: Optional[tuple[float, float]] = None
    end_pos: Optional[tuple[float, float]] = None
    target_name: Optional[str] = None
    actual_damage: float = 0.0
    description: str = ""


class CharacterSliceResult(BaseModel):
    """一个角色在一个切片内的完整结果"""
    # 状态差
    start_pos: tuple[float, float] = Field(default=(0.0, 0.0))
    start_facing: tuple[float, float] = Field(default=(0.0, 1.0))
    end_pos: tuple[float, float] = Field(default=(0.0, 0.0))
    end_facing: tuple[float, float] = Field(default=(0.0, 1.0))

    # 行为回放
    actions: list[ActionReplay] = Field(default_factory=list)

    # 感知（动画播放时 UI 展示用）
    perception_visual: list[str] = Field(default_factory=list)
    perception_auditory: list[str] = Field(default_factory=list)
    perception_tactile: list[str] = Field(default_factory=list)

    # 状态
    hp: float = 100.0
    heart_rate: str = "calm"
    drive_force: float = 0.0
    drive_breakdown: dict[str, float] = Field(default_factory=dict)
    dimension_snapshot: dict[str, float] = Field(default_factory=dict)

    # 行为输出（LLM/玩家原始行为，用于记忆写入）
    speech_content: str = ""
    thought_content: str = ""
    thought_emotion: str = ""


class SliceResult(BaseModel):
    """一个完整切片的结果（前端拿到的全部数据）"""
    slice_index: int = 0
    elapsed_label: str = "0秒"
    real_duration_ms: float = 1000.0,  # 现实播放时长（毫秒）
    characters: dict[str, CharacterSliceResult] = Field(default_factory=dict)
    world_events: list[dict] = Field(default_factory=list, description="本切片新产生的世界事件")
