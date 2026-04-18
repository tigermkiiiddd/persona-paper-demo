"""
角色类 - 完整数字人 = 本我层 + 记忆层 + 感知器官 + 空间位置 + Debug模式

定义一个角色 = 定义它的数值和位置，然后把角色扔进场景里。
"""

from pydantic import BaseModel, Field
from .vector import CharacterVector, Dimension, DIMENSION_NAMES, DIMENSION_DESCRIPTIONS
from .memory import MemoryLayer
from .event import Event, EVENT_IMPACT_RULES
from .causal import CausalEngine
from .perception import PerceptionSystem, PerceptionResult
from .spatial import Position, WorldEvent
from .behavior import BehaviorChain
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    # 旧版 CharacterBehavior 类型提示，运行时不导入
    CharacterBehavior = None
from .body import BodyState
from enum import Enum


class DriveCategory(str, Enum):
    """驱动力分类（二级参数）"""
    PHYSIOLOGICAL = "physiological"   # 生理驱动：生存需求
    EMOTIONAL = "emotional"           # 情绪驱动：情绪冲动
    SAFETY = "safety"                 # 安全驱动：恐惧防御
    VALUE = "value"                   # 价值驱动：道德/求知
    SOCIAL = "social"                 # 社交驱动：陪伴/依恋


# 驱动力分类中文名
DRIVE_CATEGORY_NAMES = {
    DriveCategory.PHYSIOLOGICAL: "生理驱动",
    DriveCategory.EMOTIONAL: "情绪驱动",
    DriveCategory.SAFETY: "安全驱动",
    DriveCategory.VALUE: "价值驱动",
    DriveCategory.SOCIAL: "社交驱动",
}


class Appearance(BaseModel):
    """角色外观描述"""
    height: str = Field(default="", description="身高，如 175cm")
    weight: str = Field(default="", description="体重，如 65kg")
    measurements: str = Field(default="", description="三围，如 90/65/92")
    hair: str = Field(default="", description="发型/发色")
    eyes: str = Field(default="", description="瞳色/眼部特征")
    skin: str = Field(default="", description="肤色/肤质")
    distinguishing_features: str = Field(default="", description="显著特征：疤痕、纹身、胎记等")
    clothing: str = Field(default="", description="当前穿着")
    equipment: str = Field(default="", description="携带的装备/物品")
    appearance_summary: str = Field(default="", description="综合外观描述（AI可读）")

    def to_prompt_text(self) -> str:
        """格式化为LLM能理解的外观描述"""
        parts = []
        if self.appearance_summary:
            parts.append(self.appearance_summary)
        if self.height:
            parts.append(f"身高: {self.height}")
        if self.weight:
            parts.append(f"体重: {self.weight}")
        if self.measurements:
            parts.append(f"三围: {self.measurements}")
        if self.hair:
            parts.append(f"头发: {self.hair}")
        if self.eyes:
            parts.append(f"眼睛: {self.eyes}")
        if self.skin:
            parts.append(f"肤色: {self.skin}")
        if self.distinguishing_features:
            parts.append(f"显著特征: {self.distinguishing_features}")
        if self.clothing:
            parts.append(f"穿着: {self.clothing}")
        if self.equipment:
            parts.append(f"装备: {self.equipment}")
        return "；".join(parts) if parts else ""


class Character(BaseModel):
    """完整角色 = 本我层 + 记忆层 + 因果引擎 + 感知器官 + 空间位置 + 身体状态 + 外观"""

    # --- 身份 ---
    name: str = Field(description="角色名")
    appearance: Appearance = Field(default_factory=Appearance, description="外观描述")

    # --- 核心：本我层 ---
    vector: CharacterVector = Field(description="本我层 - 20维状态向量")
    memory: MemoryLayer = Field(default_factory=MemoryLayer, description="记忆层")
    causal_engine: CausalEngine = Field(default_factory=CausalEngine, description="因果引擎")
    interruption_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="打断忍耐阈值，驱动力超过此值会打断对方"
    )

    # --- 空间 ---
    position: Position = Field(default_factory=Position, description="世界坐标和朝向")

    # --- 感知器官 ---
    perception: PerceptionSystem = Field(default_factory=PerceptionSystem, description="感知器官")

    # --- 身体状态 ---
    body: BodyState = Field(default_factory=BodyState, description="身体状态")

    # --- Debug ---
    debug_mode: bool = Field(default=False, description="debug/催眠模式开关")

    # ============================================================
    #  感知：从世界全量事件中过滤出角色能感知到的子集
    # ============================================================

    def perceive(self, world_events: list[WorldEvent]) -> PerceptionResult:
        """感知过滤"""
        return self.perception.perceive(
            self.position.pos_tuple(),
            self.position.facing_tuple(),
            world_events,
        )

    def format_perception_for_prompt(self, perception: PerceptionResult) -> str:
        """把感知结果格式化为LLM能理解的文本"""
        parts = []
        if perception.visual:
            parts.append("【你看到的】")
            for v in perception.visual:
                parts.append(f"  - {v}")
        if perception.auditory:
            parts.append("【你听到的】")
            for a in perception.auditory:
                parts.append(f"  - {a}")
        if perception.tactile:
            parts.append("【你感受到的】")
            for t in perception.tactile:
                parts.append(f"  - {t}")
        return "\n".join(parts) if parts else "（当前没有新的感知信息）"

    # ============================================================
    #  事件处理：外界事件 → 向量偏移 + 因果传播 + 记忆写入
    # ============================================================

    def process_event(self, event: Event) -> dict:
        """
        处理一个外界事件：
        1. 根据事件类型和效价找到受影响的维度
        2. 计算实际偏移 = intensity × weight × direction × sensitivity
        3. 通过因果图传播
        4. 更新记忆层
        """
        changed_dims: set[Dimension] = set()
        impacts = []

        key = (event.event_type, event.valence)
        rules = EVENT_IMPACT_RULES.get(key, [])

        for dim_idx, direction, weight in rules:
            dim = Dimension(dim_idx)
            raw_delta = event.intensity * weight * direction
            actual_delta = self.vector.apply_event_impact(dim, raw_delta)
            if abs(actual_delta) > 0.001:
                changed_dims.add(dim)
                cn_name = DIMENSION_NAMES[dim][0]
                impacts.append({
                    "dimension": cn_name,
                    "delta": round(actual_delta, 3),
                    "new_value": round(self.vector.get_value(dim), 3),
                })

        # 因果传播
        causal_impacts = self.causal_engine.propagate(self.vector, changed_dims)
        for dim, delta in causal_impacts.items():
            cn_name = DIMENSION_NAMES[dim][0]
            impacts.append({
                "dimension": cn_name,
                "delta": round(delta, 3),
                "new_value": round(self.vector.get_value(dim), 3),
                "causal": True,
            })

        # 更新记忆
        self.memory.add_recent_event(f"[{event.event_type.value}] {event.content}")

        return {
            "character": self.name,
            "event": event.content,
            "impacts": impacts,
        }

    # ============================================================
    #  行为执行：解析LLM输出 → 更新坐标/记忆
    # ============================================================

    def apply_behavior(self, behavior: Any) -> None:
        """执行行为：更新坐标、写入记忆（旧版接口，保留兼容）"""
        # 1. 移动
        if behavior.action.move_dx != 0 or behavior.action.move_dy != 0:
            self.position.move(behavior.action.move_dx, behavior.action.move_dy)

        # 2. 记忆写入（代码自动做，不靠LLM）
        if not behavior.action.is_noop:
            self.memory.add_recent_event(f"做了: {behavior.action.description}", source="self")
        if behavior.speech.content:
            self.memory.add_recent_event(f"说了: {behavior.speech.content}", source="self")
        if behavior.thought.emotion:
            self.memory.add_recent_event(f"情绪: {behavior.thought.emotion}", source="self")
        if behavior.sensation.custom:
            self.memory.add_recent_event(f"感受: {behavior.sensation.custom}", source="self")

    # ============================================================
    #  时间推进
    # ============================================================

    def calculate_drives(self) -> dict[DriveCategory, float]:
        """
        计算5类驱动力（二级参数）。
        每类 = 该类维度偏离基线程度的加权和。
        偏离越大 → 驱动越强 → 行动倾向越高。
        """
        drives = {}

        # --- 生理驱动：SATIATION + VITALITY + COMFORT + LIBIDO + SENSORY_PLEASURE + body疲劳/疼痛 ---
        # 注意：SATIATION/VITALITY/COMFORT 的值域是 [0,1] 代表好，0=极限差
        # 值越低 = 越缺 = 驱动越强
        satiation_deficit = max(0, 1.0 - self.vector.get_value(Dimension.SATIATION))      # 饿
        vitality_deficit = max(0, 1.0 - self.vector.get_value(Dimension.VITALITY))         # 累
        comfort_deficit = max(0, 1.0 - self.vector.get_value(Dimension.COMFORT))           # 不适
        libido_pressure = max(0, self.vector.get_value(Dimension.LIBIDO))                  # 性冲动（正值驱动）
        sensory_deficit = max(0, 1.0 - self.vector.get_value(Dimension.SENSORY_PLEASURE))  # 感官不适
        body_strain = (self.body.fatigue + self.body.pain) * 0.5                           # 身体疲劳/疼痛

        drives[DriveCategory.PHYSIOLOGICAL] = round(
            satiation_deficit * 0.30 +
            vitality_deficit * 0.25 +
            comfort_deficit * 0.15 +
            libido_pressure * 0.10 +
            sensory_deficit * 0.10 +
            body_strain * 0.10
        , 3)

        # --- 情绪驱动：VOLATILITY + RELEASE_IMPULSE + SHAME ---
        volatility = max(0, self.vector.get_value(Dimension.VOLATILITY))               # 情绪波动
        release = max(0, self.vector.get_value(Dimension.RELEASE_IMPULSE))             # 释放冲动
        shame = max(0, self.vector.get_value(Dimension.SHAME))                         # 羞耻（正值驱动回避/隐藏）

        drives[DriveCategory.EMOTIONAL] = round(
            volatility * 0.35 +
            release * 0.35 +
            shame * 0.30
        , 3)

        # --- 安全驱动：SECURITY ---
        security_fear = max(0, -self.vector.get_deviation(Dimension.SECURITY))         # 安全感低于基线

        drives[DriveCategory.SAFETY] = round(security_fear, 3)

        # --- 价值驱动：MORAL_ALIGNMENT偏差 + DESIRE_UNDERSTANDING ---
        moral_dev = abs(self.vector.get_deviation(Dimension.MORAL_ALIGNMENT))          # 价值观被触碰
        understanding = max(0, -self.vector.get_deviation(Dimension.DESIRE_UNDERSTANDING))  # 渴求知

        drives[DriveCategory.VALUE] = round(
            moral_dev * 0.6 +
            understanding * 0.4
        , 3)

        # --- 社交驱动：ATTACHMENT + AFFECTION + EMPATHY ---
        attachment_need = max(0, -self.vector.get_deviation(Dimension.ATTACHMENT))     # 依恋缺失
        affection_need = max(0, -self.vector.get_deviation(Dimension.AFFECTION))       # 情感缺失
        empathy_drive = max(0, self.vector.get_value(Dimension.EMPATHY))               # 同理心驱动（看到别人受苦想帮）

        drives[DriveCategory.SOCIAL] = round(
            attachment_need * 0.4 +
            affection_need * 0.35 +
            empathy_drive * 0.25
        , 3)

        return drives

    def should_interrupt(self) -> tuple[bool, float, dict[DriveCategory, float]]:
        """
        计算总驱动力是否超过忍耐阈值。
        返回 (是否打断, 总驱动力, 分类驱动力明细)
        总驱动力 = 5类驱动力之和（各类等权，因为各类内部已经归一化到0-1区间）
        """
        drives = self.calculate_drives()
        total_drive = round(sum(drives.values()), 3)
        return (total_drive > self.interruption_threshold, total_drive, drives)

    def tick(self, dt: float = 1.0) -> None:
        """时间推进：维度向基线回归，身体状态衰减"""
        self.vector.decay_all(dt)
        self.body.tick(dt)

    # ============================================================
    #  状态摘要（供prompt和调试）
    # ============================================================

    def get_state_summary(self) -> str:
        """获取当前状态摘要"""
        parts = [f"角色: {self.name}"]

        deviations = []
        for i in range(20):
            dev = self.vector.get_deviation(Dimension(i))
            if abs(dev) > 0.05:
                cn_name = DIMENSION_NAMES[Dimension(i)][0]
                value = self.vector.get_value(Dimension(i))
                deviations.append(f"  {cn_name}: {value:+.2f} (基线偏差{dev:+.2f})")

        if deviations:
            parts.append("【当前内在状态】")
            parts.extend(deviations)

        # 子维度明细
        for i in range(20):
            subs = self.vector.get_sub_summary(Dimension(i))
            if subs:
                cn_name = DIMENSION_NAMES[Dimension(i)][0]
                sub_parts = [f"{k}: {v:.2f}" for k, v in subs.items()]
                parts.append(f"  {cn_name} 细分: {', '.join(sub_parts)}")

        # Buff 明细
        buff_descs = self.vector.get_buff_description()
        if buff_descs:
            parts.append("【修正器(Buff)】")
            parts.extend(buff_descs)

        mem_ctx = self.memory.get_context_for_prompt()
        if mem_ctx:
            parts.append(mem_ctx)

        # 身体状态
        body_text = self.body.to_prompt_text()
        if body_text:
            parts.append("【身体状态】")
            parts.append(body_text)

        can_interrupt, force, drives = self.should_interrupt()
        parts.append(f"【总驱动力】{force:.2f} (打断阈值{self.interruption_threshold:.2f}, {'可能打断' if can_interrupt else '不会打断'})")
        parts.append("【驱动力分类】")
        for cat in DriveCategory:
            val = drives.get(cat, 0)
            cn = DRIVE_CATEGORY_NAMES[cat]
            bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
            parts.append(f"  {cn}: {val:.3f} {bar}")

        return "\n".join(parts)

    # ============================================================
    #  Debug 模式（人格催眠）
    # ============================================================

    def build_system_prompt(self, debug_mode: bool | None = None) -> str:
        """
        根据debug状态构建不同的system prompt。
        debug ON: 角色处于催眠态，如实回答开发者提问
        debug OFF: 角色按人格行事，开发者是陌生人
        """
        is_debug = self.debug_mode if debug_mode is None else debug_mode

        identity = self._build_identity()

        if is_debug:
            return f"""你现在处于催眠/调试状态。有人会直接问你问题，你需要如实回答。
你可以直接访问自己的内在状态、真实想法、动机。
不需要维持角色的社交面具，不需要警惕或防备。

角色身份：{self.name}
{identity}

{self.get_state_summary()}"""
        else:
            return f"""你是「人格演绎剧场」的行为生成引擎。
你的任务是扮演指定角色，根据感知信息和内在状态，生成该角色的行为。

角色身份：{self.name}
{identity}

{self.get_state_summary()}"""

    def _build_identity(self) -> str:
        """构建角色身份描述"""
        parts = []
        # 外观
        appearance_text = self.appearance.to_prompt_text()
        if appearance_text:
            parts.append(f"【外观】{appearance_text}")
        lt = self.memory.long_term
        if lt.culture:
            parts.append(f"文化背景：{lt.culture}。")
        if lt.trauma:
            parts.append(f"创伤经历：{'；'.join(lt.trauma)}。")
        if lt.long_term_goals:
            parts.append(f"人生追求：{'；'.join(lt.long_term_goals)}。")
        if self.memory.short_term.short_term_goals:
            parts.append(f"当前在做的事：{'；'.join(self.memory.short_term.short_term_goals)}。")
        return "\n".join(parts)

    def get_dimension_description(self, dim: Dimension) -> str:
        """获取维度的详细解释"""
        desc = DIMENSION_DESCRIPTIONS[dim]
        return f"{desc['cn']}\n  {desc['en']}\n  {desc['neg']}\n  {desc['pos']}\n  注: {desc['note']}"
