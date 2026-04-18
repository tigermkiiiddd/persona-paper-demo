"""
世界判定系统 — 规则库 + 判定引擎 + 天道

JudgeSystem 接收角色的 BehaviorAction，查规则库，
有规则→直接计算，无规则→天道介入(可选)。
"""

import math
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

from ..core.behavior import BehaviorAction, ActionType, JudgeResult
from ..core.scene import Scene


# ============================================================
#  世界法则
# ============================================================

class RuleSource(str, Enum):
    BUILTIN = "builtin"        # 内置法则
    TIANDAO = "tiandao"        # 天道生成
    MANUAL = "manual"          # 玩家/城主手动定义


class WorldRule(BaseModel):
    """一条世界法则"""
    rule_id: str = Field(description="唯一ID")
    name: str = Field(default="", description="法则名")
    description: str = Field(default="", description="自然语言描述")
    trigger_action_type: ActionType = Field(description="触发的行为类型")
    precondition: str = Field(default="", description="前置条件（自然语言）")
    formula: str = Field(default="", description="数值计算公式（自然语言描述）")
    effects: list[str] = Field(default_factory=list, description="效果列表")
    applies_to: str = Field(default="all", description="适用对象")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="可信度")
    source: RuleSource = Field(default=RuleSource.BUILTIN, description="来源")
    usage_count: int = Field(default=0, description="使用次数")


# ============================================================
#  规则注册表
# ============================================================

class RuleRegistry(BaseModel):
    """法则注册表——管理所有世界法则"""
    rules: dict[str, WorldRule] = Field(default_factory=dict)

    def register(self, rule: WorldRule) -> None:
        self.rules[rule.rule_id] = rule

    def find_match(self, action_type: ActionType) -> Optional[WorldRule]:
        """按行为类型查找匹配的法则"""
        for rule in self.rules.values():
            if rule.trigger_action_type == action_type:
                return rule
        return None

    def remove(self, rule_id: str) -> None:
        self.rules.pop(rule_id, None)

    def bump_usage(self, rule_id: str) -> None:
        if rule_id in self.rules:
            self.rules[rule_id].usage_count += 1


# ============================================================
#  内置法则
# ============================================================

def create_builtin_rules() -> RuleRegistry:
    """创建内置法则集"""
    registry = RuleRegistry()

    registry.register(WorldRule(
        rule_id="builtin_move",
        name="移动",
        trigger_action_type=ActionType.MOVE,
        description="角色向目标位置移动。受地形通行性和速度衰减影响。",
        formula="实际位移 = min(speed × duration, 到目标距离) × terrain_speed_mult",
        effects=["角色位置更新", "朝向更新为移动方向"],
        source=RuleSource.BUILTIN,
    ))

    registry.register(WorldRule(
        rule_id="builtin_attack",
        name="近战攻击",
        trigger_action_type=ActionType.ATTACK,
        description="角色对目标发动近战攻击。受距离、命中率、防御影响。",
        formula="命中判定: distance ≤ weapon_range → 命中; 实际伤害 = damage × duration × hit_rate",
        effects=["目标HP减少", "攻击者VITALITY消耗"],
        source=RuleSource.BUILTIN,
    ))

    registry.register(WorldRule(
        rule_id="builtin_interact",
        name="物体交互",
        trigger_action_type=ActionType.INTERACT,
        description="角色与场景物体交互。受距离和物体属性影响。",
        formula="距离判定: distance(actor, object) ≤ 1.5格",
        effects=["物体状态变化", "角色可能获得物品/信息"],
        source=RuleSource.BUILTIN,
    ))

    registry.register(WorldRule(
        rule_id="builtin_social",
        name="社交行为",
        trigger_action_type=ActionType.SOCIAL,
        description="角色说话或做肢体语言。说话传播距离受音量影响。",
        formula="传播距离: whisper=5m, normal=15m, loud=25m, shout=35m",
        effects=["其他角色接收到听觉/视觉事件", "可能触发人际关系变化"],
        source=RuleSource.BUILTIN,
    ))

    registry.register(WorldRule(
        rule_id="builtin_flee",
        name="逃跑",
        trigger_action_type=ActionType.FLEE,
        description="角色朝反方向快速移动。速度加成但消耗更多VITALITY。",
        formula="逃跑速度 = speed × 1.3, VITALITY消耗 × 1.5",
        effects=["位置更新", "VITALITY额外消耗"],
        source=RuleSource.BUILTIN,
    ))

    registry.register(WorldRule(
        rule_id="builtin_defend",
        name="防御",
        trigger_action_type=ActionType.DEFEND,
        description="角色进入防御姿态，降低受到的伤害。",
        formula="伤害减免 = 50%, 成功率 = f(独立性, 风险承受)",
        effects=["受到伤害减半", "无法同时做其他动作"],
        source=RuleSource.BUILTIN,
    ))

    registry.register(WorldRule(
        rule_id="builtin_wait",
        name="等待",
        trigger_action_type=ActionType.WAIT,
        description="角色原地不动。",
        formula="无位移，时间流逝",
        effects=["无"],
        source=RuleSource.BUILTIN,
    ))

    return registry


# ============================================================
#  世界状态（传给判定的上下文）
# ============================================================

class WorldState(BaseModel):
    """世界状态快照——判定时需要的上下文"""
    scene: Optional[Scene] = None
    character_positions: dict[str, tuple[float, float]] = Field(default_factory=dict)
    character_facing: dict[str, tuple[float, float]] = Field(default_factory=dict)
    character_hp: dict[str, float] = Field(default_factory=dict)
    # 角色维度值（用于推导二级属性）
    character_dimensions: dict[str, list[float]] = Field(
        default_factory=dict,
        description="角色名→20维值列表",
    )
    # 角色当前是否在防御状态
    character_defending: dict[str, bool] = Field(default_factory=dict)
    # 身体素质二级参数（由20维推导或手动覆盖）
    character_physique: dict[str, "PhysiqueParams"] = Field(default_factory=dict)
    slice_index: int = 0

    def get_dim(self, name: str, index: int) -> float:
        """获取某角色的某维度值"""
        dims = self.character_dimensions.get(name)
        if dims and 0 <= index < len(dims):
            return dims[index]
        return 0.0

    def get_physique(self, name: str) -> "PhysiqueParams":
        """获取角色的身体素质参数，没有则从维度推导"""
        if name in self.character_physique:
            return self.character_physique[name]
        dims = self.character_dimensions.get(name, [0.0] * 20)
        return derive_physique(dims)


# ============================================================
#  身体素质二级参数
# ============================================================

class PhysiqueParams(BaseModel):
    """
    身体素质二级参数——从20维推导的战斗/运动能力值

    这些是"你能做到什么"的客观能力，不是概率。
    也可以手动覆盖（装备/状态效果）。
    所有值范围 [0.0, 1.0]（move_speed 除外）。

    判定逻辑：能力值对抗，不是掷骰。
    - attack_power vs dodge_capability → 能否闪避
    - attack_power vs block_capability → 能否格挡
    - 角色的策略选择（闪还是挡）由 BehaviorChain 决定，不在这里
    """
    # 进攻能力
    attack_power: float = Field(default=0.5, description="攻击力（影响伤害和击穿格挡的能力）")
    attack_speed: float = Field(default=0.5, description="出招速度（影响攻击效率）")
    weapon_range: float = Field(default=1.5, description="默认攻击范围（格）")

    # 防守能力
    dodge_capability: float = Field(default=0.3, description="闪避能力（反应速度+灵活性，对抗攻击者的attack_power）")
    block_capability: float = Field(default=0.3, description="格挡能力（力量+技术，对抗攻击者的attack_power）")
    block_efficiency: float = Field(default=0.5, description="格挡减伤比例（格挡成功时减伤多少，0.5=减半）")
    parry_capability: float = Field(default=0.2, description="招架能力（反击型防御，格挡成功后反弹伤害的能力）")

    # 感知判断
    combat_perception: float = Field(default=0.3, description="战况判断力（估计对手实力的准确度）")

    # 移动
    move_speed: float = Field(default=5.0, description="移动速度（格/分钟）")
    sprint_mult: float = Field(default=1.3, description="冲刺/逃跑速度倍率")

    # 耐力
    stamina_efficiency: float = Field(default=1.0, description="体力效率（越高消耗越少）")
    recovery_rate: float = Field(default=0.5, description="自然恢复速率系数")

    # 韧性
    damage_resistance: float = Field(default=0.0, description="固定减伤比例（护甲/体质）")
    pain_tolerance: float = Field(default=0.5, description="忍痛能力（影响受伤后的行动惩罚）")


def derive_physique(dims: list[float]) -> PhysiqueParams:
    """
    从20维本我向量推导身体素质二级参数

    推导逻辑（维度→身体素质的映射关系）：
    - VITALITY(10) → 体力、恢复、耐力
    - INDEPENDENCE(2) → 不被压制、敢反击
    - RISK_TOLERANCE(7) → 敢赌闪避、敢冒险
    - VOLATILITY(4) → 爆发力（情绪波动大=突然加速）
    - DOMINANCE(0) → 攻击欲望
    - PRAGMATISM(3) → 战术判断（格挡/招架时机）
    - SELF_ESTEEM(6) → 不怯场
    - RELEASE_IMPULSE(19) → 攻击速度（冲动=出手快）
    """
    # 安全取值
    def d(idx: int) -> float:
        return dims[idx] if 0 <= idx < len(dims) else 0.0

    vitality = d(10)       # [0,1]
    independence = d(2)    # [-1,1]
    risk = d(7)            # [-1,1]
    volatility = d(4)      # [-1,1]
    dominance = d(0)       # [-1,1]
    pragmatism = d(3)      # [-1,1]
    self_esteem = d(6)     # [-1,1]
    release = d(19)        # [-1,1]
    empathy = d(8)         # [-1,1]

    # 归一化到 [0,1]（维度范围 [-1,1] → 映射到 [0,1]）
    def norm(v: float) -> float:
        return (v + 1.0) / 2.0

    return PhysiqueParams(
        # 进攻：DOMINANCE驱动攻击欲望，VITALITY提供力量，RELEASE_IMPULSE加速
        attack_power=0.3 + vitality * 0.3 + norm(dominance) * 0.2 + norm(release) * 0.2,
        attack_speed=0.3 + norm(release) * 0.3 + vitality * 0.2 + norm(volatility) * 0.2,
        weapon_range=1.5,  # 默认近战，武器可覆盖

        # 防守能力：VITALITY=反应速度，INDEPENDENCE=不被压制
        dodge_capability=0.1 + vitality * 0.3 + norm(independence) * 0.15 + norm(risk) * 0.05,
        block_capability=0.1 + vitality * 0.2 + norm(pragmatism) * 0.25 + norm(independence) * 0.1,
        block_efficiency=0.4 + norm(pragmatism) * 0.2,  # 格挡效率 40%-60%
        parry_capability=0.05 + norm(dominance) * 0.15 + norm(pragmatism) * 0.15,  # 招架=反击型

        # 感知判断：PRAGMATISM+SELF_ESTEEM→冷静评估
        combat_perception=0.1 + norm(pragmatism) * 0.3 + norm(self_esteem) * 0.15 + norm(risk) * 0.1,

        # 移动：VITALITY×速度基数
        move_speed=3.0 + vitality * 5.0,  # 3-8 格/分钟
        sprint_mult=1.3,

        # 耐力
        stamina_efficiency=0.5 + vitality * 0.5,
        recovery_rate=0.2 + vitality * 0.6,

        # 韧性：高VITALITY=抗揍，低EMPATHY=硬扛
        damage_resistance=vitality * 0.15 + (1.0 - norm(empathy)) * 0.05,
        pain_tolerance=0.3 + vitality * 0.3 + norm(independence) * 0.2,
    )


# ============================================================
#  判定引擎
# ============================================================

class JudgeSystem:
    """
    世界判定引擎
    
    接收 BehaviorAction，查规则库，执行判定，返回 JudgeResult。
    """

    def __init__(self, rule_registry: Optional[RuleRegistry] = None, tiandao_system=None):
        self.rule_registry = rule_registry or create_builtin_rules()
        self.tiandao_enabled: bool = True
        self.tiandao_system = tiandao_system  # TiandaoSystem 实例，None=天道未启用

    def judge(
        self,
        action: BehaviorAction,
        actor_name: str,
        world_state: WorldState,
    ) -> JudgeResult:
        """判定单条 action"""

        # 查规则
        rule = self.rule_registry.find_match(action.type)

        if rule is None:
            # 无规则
            if self.tiandao_enabled and action.type == ActionType.CUSTOM:
                return self._judge_custom(action, actor_name, world_state)
            return JudgeResult(
                action_type=action.type,
                success=False,
                reason=f"无匹配法则: {action.type.value}",
            )

        # 有规则，执行计算
        self.rule_registry.bump_usage(rule.rule_id)

        handler = {
            ActionType.MOVE: self._judge_move,
            ActionType.ATTACK: self._judge_attack,
            ActionType.INTERACT: self._judge_interact,
            ActionType.SOCIAL: self._judge_social,
            ActionType.FLEE: self._judge_flee,
            ActionType.DEFEND: self._judge_defend,
            ActionType.WAIT: self._judge_wait,
        }.get(action.type)

        if handler:
            return handler(action, actor_name, world_state)

        return JudgeResult(
            action_type=action.type,
            success=False,
            reason=f"未实现的判定类型: {action.type.value}",
        )

    # ---- 具体判定 ----

    def _judge_move(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """移动判定：地形通行性 + 速度衰减"""
        start = ws.character_positions.get(actor_name, (0.0, 0.0))
        target = (action.target_x or start[0], action.target_y or start[1])

        # 计算目标距离
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        target_dist = math.sqrt(dx * dx + dy * dy)
        if target_dist < 0.01:
            return JudgeResult(
                action_type=ActionType.MOVE, success=True,
                actual_end_x=start[0], actual_end_y=start[1],
                broadcast_content=f"{actor_name}站在原地",
            )

        # 理论最大位移
        max_move = action.speed * action.duration

        # 地形影响（如果有场景）
        speed_mult = 1.0
        if ws.scene:
            # 检查目标格的地形
            tx, ty = int(target[0]), int(target[1])
            tile = ws.scene.get_tile(tx, ty)
            if tile:
                from .scene import TERRAIN_PROPS
                props = TERRAIN_PROPS.get(tile.terrain, {})
                if not props.get("passable", True):
                    # 不可通行，移到最近的可行位置
                    dir_x = dx / target_dist
                    dir_y = dy / target_dist
                    # 逐步逼近找最近的可行点
                    actual_dist = 0
                    step = 0.5
                    while actual_dist + step < max_move:
                        test_x = start[0] + dir_x * (actual_dist + step)
                        test_y = start[1] + dir_y * (actual_dist + step)
                        t_tile = ws.scene.get_tile(int(test_x), int(test_y))
                        if t_tile:
                            t_props = TERRAIN_PROPS.get(t_tile.terrain, {})
                            if not t_props.get("passable", True):
                                break
                            speed_mult = t_props.get("speed_mult", 1.0)
                        actual_dist += step
                    max_move = actual_dist
                else:
                    speed_mult = props.get("speed_mult", 1.0)

        # 实际位移
        actual_dist = min(max_move * speed_mult, target_dist)
        ratio = actual_dist / target_dist if target_dist > 0 else 0
        end_x = start[0] + dx * ratio
        end_y = start[1] + dy * ratio

        # 朝向
        move_dx = end_x - start[0]
        move_dy = end_y - start[1]
        move_len = math.sqrt(move_dx ** 2 + move_dy ** 2)

        desc = f"{actor_name}向({target[0]:.0f},{target[1]:.0f})移动"
        if actual_dist < target_dist * 0.9:
            desc += f"（走了{actual_dist:.1f}格，因地形受阻）"

        return JudgeResult(
            action_type=ActionType.MOVE,
            success=True,
            actual_dx=end_x - start[0],
            actual_dy=end_y - start[1],
            actual_end_x=round(end_x, 2),
            actual_end_y=round(end_y, 2),
            broadcast_content=desc,
            broadcast_type="visual",
            broadcast_valence="neutral",
        )

    def _judge_attack(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """
        攻击判定：距离 → 命中 → 防守方策略应对 → 实际伤害

        核心机制：能力值对抗，不是掷骰
        - 攻击效果 = attack_power × attack_speed
        - 防守方的策略由 BehaviorChain 决定（defend/dodge 动作）
        - JudgeSystem 只算结果：攻方能力 vs 守方能力
        - 能力差决定结果，不是随机数
        """
        actor_pos = ws.character_positions.get(actor_name, (0.0, 0.0))
        target_name = action.target_name or ""

        if target_name not in ws.character_positions:
            return JudgeResult(
                action_type=ActionType.ATTACK, success=False,
                reason=f"目标不存在: {target_name}",
            )

        # 获取双方身体素质
        actor_ph = ws.get_physique(actor_name)
        target_ph = ws.get_physique(target_name)

        target_pos = ws.character_positions[target_name]
        dist = math.sqrt(
            (actor_pos[0] - target_pos[0]) ** 2 +
            (actor_pos[1] - target_pos[1]) ** 2
        )

        # 1. 距离判定
        weapon_range = action.weapon_range or actor_ph.weapon_range
        if dist > weapon_range:
            return JudgeResult(
                action_type=ActionType.ATTACK, success=False,
                reason=f"目标太远（距离{dist:.1f}格 > 范围{weapon_range:.1f}格）",
                broadcast_content=f"{actor_name}试图攻击{target_name}但够不到",
                broadcast_type="visual",
                broadcast_valence="negative",
            )

        # 2. 命中率（受距离衰减，这是物理事实不是随机）
        hit_rate = max(0.3, 0.8 - (dist / weapon_range) * 0.3)

        # 3. 攻击有效力 = attack_power × attack_speed × 命中率
        attack_effective = actor_ph.attack_power * (0.5 + actor_ph.attack_speed * 0.5) * hit_rate

        # 4. 防守方的策略（从 BehaviorChain 的 defend 状态读取）
        is_defending = ws.character_defending.get(target_name, False)

        if is_defending:
            # 防守方选择了格挡 → attack_effective vs block_capability
            if attack_effective <= target_ph.block_capability:
                # 格挡成功
                actual_dmg = action.damage * action.duration * (1.0 - target_ph.block_efficiency)
                # 招架检定：格挡成功后能不能反击
                parry_dmg = 0.0
                if target_ph.parry_capability > actor_ph.attack_power * 0.5:
                    parry_dmg = attack_effective * target_ph.parry_capability * 0.5
                    desc = f"{actor_name}攻击{target_name}，被{target_name}招架格挡，反震{parry_dmg:.1f}点"
                else:
                    desc = f"{actor_name}攻击{target_name}，被{target_name}格挡（减伤{target_ph.block_efficiency:.0%}）"
            else:
                # 攻击击穿格挡（攻方太猛）
                overrun_ratio = (attack_effective - target_ph.block_capability) / max(attack_effective, 0.01)
                actual_dmg = action.damage * action.duration * overrun_ratio
                desc = f"{actor_name}的攻击击穿了{target_name}的格挡"
        else:
            # 防守方没有防御动作，但可能靠本能闪避
            # 本能闪避 = dodge_capability vs attack_effective
            if target_ph.dodge_capability > attack_effective:
                # 反应快，本能躲开
                return JudgeResult(
                    action_type=ActionType.ATTACK,
                    success=False,
                    reason=f"{target_name}闪避了攻击（闪避能力{target_ph.dodge_capability:.2f} > 攻击有效力{attack_effective:.2f}）",
                    actual_damage=0.0,
                    target_name=target_name,
                    broadcast_content=f"{actor_name}攻击{target_name}，{target_name}侧身闪开了",
                    broadcast_type="visual",
                    broadcast_valence="neutral",
                )
            actual_dmg = action.damage * action.duration
            desc = f"{actor_name}击中{target_name}"

        # 5. 基础伤害 × hit_rate（远距离擦伤）
        actual_dmg *= hit_rate

        # 6. 固定减伤（护甲/体质）
        actual_dmg = actual_dmg * (1.0 - target_ph.damage_resistance)

        if hit_rate < 0.6:
            desc += "（擦伤）"

        return JudgeResult(
            action_type=ActionType.ATTACK,
            success=True,
            actual_damage=round(actual_dmg, 2),
            target_name=target_name,
            broadcast_content=desc,
            broadcast_type="visual",
            broadcast_valence="negative",
        )

    def _judge_interact(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """物体交互判定"""
        actor_pos = ws.character_positions.get(actor_name, (0.0, 0.0))

        if not action.object_id or not ws.scene:
            return JudgeResult(
                action_type=ActionType.INTERACT, success=False,
                reason="无目标物体或无场景",
            )

        # 找物体
        obj = None
        for o in ws.scene.objects:
            if o.id == action.object_id:
                obj = o
                break

        if obj is None:
            return JudgeResult(
                action_type=ActionType.INTERACT, success=False,
                reason=f"物体不存在: {action.object_id}",
            )

        # 距离判定
        dist = math.sqrt(
            (actor_pos[0] - obj.x) ** 2 + (actor_pos[1] - obj.y) ** 2
        )
        if dist > 1.5:
            return JudgeResult(
                action_type=ActionType.INTERACT, success=False,
                reason=f"物体太远（距离{dist:.1f}格 > 1.5格）",
            )

        desc = f"{actor_name}与{obj.name or obj.id}交互"
        if action.interact_type:
            desc = f"{actor_name}{action.interact_type}了{obj.name or obj.id}"

        return JudgeResult(
            action_type=ActionType.INTERACT,
            success=True,
            broadcast_content=desc,
            broadcast_type="visual",
            broadcast_valence="neutral",
        )

    def _judge_social(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """社交判定：说话/手势"""
        desc = ""
        evt_type = "visual"

        if action.speech_content:
            vol_map = {"whisper": "低声", "normal": "", "loud": "大声", "shout": "喊道"}
            vol_label = vol_map.get(action.speech_volume, "")
            desc = f"{actor_name}{vol_label}说：「{action.speech_content}」"
            evt_type = "auditory"
        elif action.gesture:
            desc = f"{actor_name}{action.gesture}"

        return JudgeResult(
            action_type=ActionType.SOCIAL,
            success=True,
            broadcast_content=desc or f"{actor_name}做了一个社交动作",
            broadcast_type=evt_type,
            broadcast_valence="neutral",
        )

    def _judge_flee(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """逃跑判定：速度×1.3，VITALITY消耗×1.5"""
        start = ws.character_positions.get(actor_name, (0.0, 0.0))
        flee_speed = action.speed * 1.3
        max_dist = flee_speed * action.duration

        dir_x = action.flee_direction_x or 0.0
        dir_y = action.flee_direction_y or 0.0
        dir_len = math.sqrt(dir_x ** 2 + dir_y ** 2)
        if dir_len < 0.01:
            dir_x, dir_y = 0.0, -1.0  # 默认向北跑
            dir_len = 1.0

        end_x = start[0] + (dir_x / dir_len) * max_dist
        end_y = start[1] + (dir_y / dir_len) * max_dist

        return JudgeResult(
            action_type=ActionType.FLEE,
            success=True,
            actual_dx=end_x - start[0],
            actual_dy=end_y - start[1],
            actual_end_x=round(end_x, 2),
            actual_end_y=round(end_y, 2),
            broadcast_content=f"{actor_name}转身逃跑",
            broadcast_type="visual",
            broadcast_valence="negative",
        )

    def _judge_defend(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """防御判定"""
        return JudgeResult(
            action_type=ActionType.DEFEND,
            success=True,
            broadcast_content=f"{actor_name}摆出防御姿态",
            broadcast_type="visual",
            broadcast_valence="neutral",
        )

    def _judge_wait(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """等待"""
        return JudgeResult(
            action_type=ActionType.WAIT,
            success=True,
            broadcast_content="",
        )

    def _judge_custom(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> JudgeResult:
        """自定义行为——天道介入判定"""
        if self.tiandao_system is None:
            return JudgeResult(
                action_type=ActionType.CUSTOM,
                success=False,
                reason="天道系统未启用",
            )

        result = self.tiandao_system.judge_custom(action, actor_name, ws)
        # 同步法则到本 JudgeSystem 的 registry
        self.rule_registry.register(result.rule)
        jr = result.judge_result
        jr.new_rule_id = result.rule.rule_id
        return jr
