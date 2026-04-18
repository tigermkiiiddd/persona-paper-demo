"""
角色向量系统 - 20维本我层

性格驱动器（前10维，慢变）+ 生理/欲望驱动器（后10维，快变）
每个维度有：当前值、基线值、敏感度、回归速率
所有值范围 [-1.0, 1.0]
"""

from enum import IntEnum, Enum
from pydantic import BaseModel, Field


class Trait(IntEnum):
    """性格驱动器（核心人格倾向，慢变）"""
    DOMINANCE = 0           # 掌控欲
    AFFECTION = 1           # 亲和度
    INDEPENDENCE = 2        # 独立性
    PRAGMATISM = 3          # 务实性
    VOLATILITY = 4          # 情绪波动
    CURIOSITY = 5           # 好奇心
    SELF_ESTEEM = 6         # 自尊心
    RISK_TOLERANCE = 7      # 风险承受
    EMPATHY = 8             # 同理心
    MORAL_ALIGNMENT = 9     # 道德准则


class Drive(IntEnum):
    """生理/欲望驱动器（原始本能与深层渴望，快变）"""
    VITALITY = 10               # 生命力
    SATIATION = 11              # 饥饿/口渴
    SECURITY = 12               # 安全感
    COMFORT = 13                # 舒适度
    LIBIDO = 14                 # 性冲动
    DESIRE_UNDERSTANDING = 15   # 渴望被理解
    SHAME = 16                  # 羞耻感
    SENSORY_PLEASURE = 17       # 感官愉悦
    ATTACHMENT = 18             # 依恋需求
    RELEASE_IMPULSE = 19        # 释放冲动


class Dimension(IntEnum):
    """全部20个维度"""
    DOMINANCE = 0
    AFFECTION = 1
    INDEPENDENCE = 2
    PRAGMATISM = 3
    VOLATILITY = 4
    CURIOSITY = 5
    SELF_ESTEEM = 6
    RISK_TOLERANCE = 7
    EMPATHY = 8
    MORAL_ALIGNMENT = 9
    VITALITY = 10
    SATIATION = 11
    SECURITY = 12
    COMFORT = 13
    LIBIDO = 14
    DESIRE_UNDERSTANDING = 15
    SHAME = 16
    SENSORY_PLEASURE = 17
    ATTACHMENT = 18
    RELEASE_IMPULSE = 19


# 维度中英文映射
DIMENSION_NAMES: dict[Dimension, tuple[str, str]] = {
    Dimension.DOMINANCE: ("掌控欲", "Dominance"),
    Dimension.AFFECTION: ("亲和度", "Affection"),
    Dimension.INDEPENDENCE: ("独立性", "Independence"),
    Dimension.PRAGMATISM: ("务实性", "Pragmatism"),
    Dimension.VOLATILITY: ("情绪波动", "Volatility"),
    Dimension.CURIOSITY: ("好奇心", "Curiosity"),
    Dimension.SELF_ESTEEM: ("自尊心", "Self-Esteem"),
    Dimension.RISK_TOLERANCE: ("风险承受", "Risk-Tolerance"),
    Dimension.EMPATHY: ("同理心", "Empathy"),
    Dimension.MORAL_ALIGNMENT: ("道德准则", "Moral-Alignment"),
    Dimension.VITALITY: ("生命力", "Vitality"),
    Dimension.SATIATION: ("饥饿/口渴", "Satiation"),
    Dimension.SECURITY: ("安全感", "Security"),
    Dimension.COMFORT: ("舒适度", "Comfort"),
    Dimension.LIBIDO: ("性冲动", "Libido"),
    Dimension.DESIRE_UNDERSTANDING: ("渴望被理解", "Desire for Understanding"),
    Dimension.SHAME: ("羞耻感", "Shame"),
    Dimension.SENSORY_PLEASURE: ("感官愉悦", "Sensory Pleasure"),
    Dimension.ATTACHMENT: ("依恋需求", "Attachment"),
    Dimension.RELEASE_IMPULSE: ("释放冲动", "Release Impulse"),
}

# 每个维度的详细解释，供LLM理解用
DIMENSION_DESCRIPTIONS: dict[Dimension, dict[str, str]] = {
    Dimension.DOMINANCE: {
        "cn": "掌控欲 - 对他人和局势的控制欲望",
        "en": "Dominance - Desire to control others and situations",
        "neg": "-1.0 = 完全顺从，听从他人安排，不争夺主导权",
        "pos": "+1.0 = 绝对主导，必须掌控一切，无法容忍被领导",
        "note": "不等于领导能力，是'想要控制'的欲望，不是'能够控制'的能力",
    },
    Dimension.AFFECTION: {
        "cn": "亲和度 - 对他人的友好程度和善意倾向",
        "en": "Affection - Tendency toward friendliness and goodwill toward others",
        "neg": "-1.0 = 极端敌意，默认对所有人抱有敌意和不信任",
        "pos": "+1.0 = 极致友好，默认信任和善待所有人",
        "note": "是内在倾向，不是外在表现。低亲和的人可以伪装友好，但内心不友好",
    },
    Dimension.INDEPENDENCE: {
        "cn": "独立性 - 不依赖他人、自主决策的倾向",
        "en": "Independence - Tendency toward self-reliance and autonomous decision-making",
        "neg": "-1.0 = 完全依赖，无法独自做决定，需要他人指引",
        "pos": "+1.0 = 绝对自主，排斥一切外部帮助和意见",
        "note": "高独立不等于高能力，是'不需要别人'的心态",
    },
    Dimension.PRAGMATISM: {
        "cn": "务实性 - 理性vs感性的思维偏向",
        "en": "Pragmatism - Thinking style: rational vs emotional",
        "neg": "-1.0 = 完全感性，凭直觉和情感做判断",
        "pos": "+1.0 = 绝对理性，一切以逻辑和事实为依据",
        "note": "不是'对错'的衡量，是思维方式的偏向。感性不等于错误，理性不等于正确",
    },
    Dimension.VOLATILITY: {
        "cn": "情绪波动 - 情绪的稳定程度（元属性，描述情绪容不容易变）",
        "en": "Volatility - How easily emotions shift (meta-property: emotional stability)",
        "neg": "-1.0 = 情绪极度稳定，几乎不受外界影响",
        "pos": "+1.0 = 极度易变，一点小事就情绪剧烈波动",
        "note": "这不是具体的情绪，而是'情绪容不容易变'这个元属性。它影响所有情绪状态的幅度和变化速度",
    },
    Dimension.CURIOSITY: {
        "cn": "好奇心 - 对未知事物的探索欲望",
        "en": "Curiosity - Desire to explore the unknown",
        "neg": "-1.0 = 完全封闭，对新事物毫无兴趣甚至排斥",
        "pos": "+1.0 = 极致探索，对一切未知都充满好奇",
        "note": "驱动探索行为和主动获取信息，低好奇心的人不会主动了解新事物",
    },
    Dimension.SELF_ESTEEM: {
        "cn": "自尊心 - 对自我价值的评价",
        "en": "Self-Esteem - Evaluation of one's own worth",
        "neg": "-1.0 = 极度自卑，认为自己毫无价值",
        "pos": "+1.0 = 极致自信，认为自己极其优秀",
        "note": "影响对批评的敏感度和对成就的需求。低自尊容易被打击但不是脆弱，高自尊可能自负",
    },
    Dimension.RISK_TOLERANCE: {
        "cn": "风险承受 - 面对风险和不确定性的容忍度",
        "en": "Risk-Tolerance - Tolerance for risk and uncertainty",
        "neg": "-1.0 = 完全规避，拒绝一切有风险的选择",
        "pos": "+1.0 = 极致冒险，主动追求高风险高回报",
        "note": "不等于勇气。高风险承受的人可能只是不在乎后果，低风险承受的人可能很勇敢但选择谨慎",
    },
    Dimension.EMPATHY: {
        "cn": "同理心 - 感知和理解他人情感的能力",
        "en": "Empathy - Ability to perceive and understand others' emotions",
        "neg": "-1.0 = 完全冷酷，无法或不愿感知他人感受",
        "pos": "+1.0 = 极致共情，能深度感受他人的喜怒哀乐",
        "note": "是感知能力，不是行为。低同理心不等于恶意，高同理心不等于善良（可能感知到了但不在乎）",
    },
    Dimension.MORAL_ALIGNMENT: {
        "cn": "道德准则 - 对规则、原则和伦理的坚守程度",
        "en": "Moral-Alignment - Adherence to rules, principles, and ethics",
        "neg": "-1.0 = 完全机会主义，为达目的不择手段",
        "pos": "+1.0 = 极致坚守，宁可吃亏也不违背原则",
        "note": "不定义具体的道德内容（什么是善什么是恶），只描述'有多在意原则'这个程度。具体道德观由记忆层的三观系统决定",
    },
    Dimension.VITALITY: {
        "cn": "生命力 - 身体和精神能量的充沛程度",
        "en": "Vitality - Physical and mental energy level",
        "neg": "-1.0 = 濒死/枯竭，没有力气做任何事",
        "pos": "+1.0 = 巅峰活力，精力充沛",
        "note": "影响行动能力和主动性。生命力低的人不想动、不想社交、不想探索",
    },
    Dimension.SATIATION: {
        "cn": "饥饿/口渴 - 生理上的满足程度",
        "en": "Satiation - Level of physical hunger/thirst satisfaction",
        "neg": "-1.0 = 极度饥渴，生理需求紧急",
        "pos": "+1.0 = 完全满足，没有任何饥渴感",
        "note": "这是'满足度'不是'饥饿度'。值越低越饿。随时间自然衰减（满足度下降=越来越饿）",
    },
    Dimension.SECURITY: {
        "cn": "安全感 - 感受到的安全程度，底层生理级的安全感知",
        "en": "Security - Perceived safety level, primal-level safety sensing",
        "neg": "-1.0 = 极度恐惧，感觉随时有生命危险",
        "pos": "+1.0 = 完全安心，没有任何威胁感",
        "note": "比舒适度更底层。安全感是'会不会死'级别，舒适度是'过得爽不爽'级别。可以在战壕里很有安全感但极度不舒适",
    },
    Dimension.COMFORT: {
        "cn": "舒适度 - 当前环境的舒适感受",
        "en": "Comfort - Current environmental comfort level",
        "neg": "-1.0 = 极度不适，环境恶劣（冷/热/疼/累）",
        "pos": "+1.0 = 完全舒适，环境宜人",
        "note": "受多个维度影响（饥饿→不适、安全感低→不适）。和安全感不同：躺豪华酒店可能很舒适但极度不安全",
    },
    Dimension.LIBIDO: {
        "cn": "性冲动 - 性方面的欲望强度",
        "en": "Libido - Intensity of sexual desire",
        "neg": "-1.0 = 完全排斥，对性毫无兴趣甚至厌恶",
        "pos": "+1.0 = 极致渴望，性需求强烈",
        "note": "是内驱力，不是行为。高性冲动不等于会实施性行为（道德准则可能压制）",
    },
    Dimension.DESIRE_UNDERSTANDING: {
        "cn": "渴望被理解 - 希望他人理解自己内心世界的程度",
        "en": "Desire for Understanding - Need to be intellectually/emotionally understood",
        "neg": "-1.0 = 完全封闭，不在乎是否有人理解自己",
        "pos": "+1.0 = 极致渴望，极度需要被理解",
        "note": "不同于依恋需求。依恋是'需要陪伴'，渴望被理解是'需要被懂'。可以很独立但极度渴望被理解",
    },
    Dimension.SHAME: {
        "cn": "羞耻感 - 产生羞耻情绪的敏感度",
        "en": "Shame - Sensitivity to feeling ashamed",
        "neg": "-1.0 = 完全无耻，做任何事都不会感到羞耻",
        "pos": "+1.0 = 极致羞耻，极易感到丢脸和羞愧",
        "note": "和自尊心独立。高自尊的人也可能高羞耻（自信但怕丢脸），低自尊的人可能低羞耻（觉得自己本来就不好没什么可丢的）",
    },
    Dimension.SENSORY_PLEASURE: {
        "cn": "感官愉悦 - 对感官刺激（味觉、听觉、触觉等）的追求和敏感度",
        "en": "Sensory Pleasure - Sensitivity to and pursuit of sensory stimulation",
        "neg": "-1.0 = 完全麻木，对感官体验毫无感觉",
        "pos": "+1.0 = 极致愉悦，极度追求美食、音乐、触感等感官享受",
        "note": "不同于舒适度。感官愉悦是多巴胺级别的（美食、音乐），舒适度是环境级别的（温度合适、不疼）。可以躺在按摩椅上很舒适但没有强烈的感官刺激",
    },
    Dimension.ATTACHMENT: {
        "cn": "依恋需求 - 对他人情感陪伴和依附的需求程度",
        "en": "Attachment - Need for emotional closeness and dependency on others",
        "neg": "-1.0 = 完全疏离，不需要任何人的情感陪伴",
        "pos": "+1.0 = 极致依恋，无法忍受独处，极度需要他人陪伴",
        "note": "和渴望被理解不同。依恋是'需要你在身边'，渴望被理解是'需要你懂我'。可以很依恋但不在乎被理解",
    },
    Dimension.RELEASE_IMPULSE: {
        "cn": "释放冲动 - 做出过激行为的倾向（外部行为层面）",
        "en": "Release Impulse - Tendency toward extreme or impulsive outward behavior",
        "neg": "-1.0 = 完全压抑，绝对不会做出任何过激行为",
        "pos": "+1.0 = 极致宣泄，极易爆发、动手、砸东西、大吼",
        "note": "是行为层面，不是情绪层面。情绪波动是内部状态（稳不稳），释放冲动是外部行为（做不做过激的事）。可以情绪很波动但从不做过激的事",
    },
}


class SubDimension(BaseModel):
    """子维度 — 生理维度的细分组分"""
    name: str = Field(description="子维度名称，如 food/water/stamina")
    value: float = Field(default=1.0, ge=-1.0, le=1.0, description="当前值")
    baseline: float = Field(default=0.0, ge=-1.0, le=1.0, description="基线值（衰减目标）")
    decay_rate: float = Field(default=0.05, ge=0.0, le=1.0, description="衰减速率")
    weight: float = Field(default=1.0, ge=0.0, description="聚合到顶层维度时的权重")


# ============================================================
#  预设子维度模板 — 生理维度的标准细分
# ============================================================

SUB_DIMENSION_TEMPLATES: dict[int, dict[str, dict]] = {
    10: {  # VITALITY
        "stamina":   {"weight": 0.40, "decay_rate": 0.04, "baseline": 0.0},
        "mental":    {"weight": 0.35, "decay_rate": 0.03, "baseline": 0.0},
        "sleep_debt":{"weight": 0.25, "decay_rate": 0.01, "baseline": 0.0},
    },
    11: {  # SATIATION
        "food":       {"weight": 0.35, "decay_rate": 0.06, "baseline": 0.0},
        "water":      {"weight": 0.30, "decay_rate": 0.08, "baseline": 0.0},
        "electrolyte":{"weight": 0.20, "decay_rate": 0.04, "baseline": 0.0},
        "vitamin":    {"weight": 0.15, "decay_rate": 0.02, "baseline": 0.0},
    },
    12: {  # SECURITY
        "physical_threat": {"weight": 0.40, "decay_rate": 0.02, "baseline": 0.0},
        "social_threat":   {"weight": 0.30, "decay_rate": 0.02, "baseline": 0.0},
        "existential":     {"weight": 0.30, "decay_rate": 0.01, "baseline": 0.0},
    },
    13: {  # COMFORT
        "temperature": {"weight": 0.30, "decay_rate": 0.03, "baseline": 0.0},
        "posture":     {"weight": 0.40, "decay_rate": 0.06, "baseline": 0.0},
        "environment": {"weight": 0.30, "decay_rate": 0.02, "baseline": 0.0},
    },
}


def build_default_sub_dimensions(dim_index: int) -> dict[str, SubDimension]:
    """根据维度索引生成预设子维度。无模板的维度返回空dict。"""
    template = SUB_DIMENSION_TEMPLATES.get(dim_index, {})
    return {
        name: SubDimension(name=name, **cfg)
        for name, cfg in template.items()
    }


class BuffTarget(str, Enum):
    """buff 可修正的目标属性"""
    BASELINE = "baseline"           # 基线值
    DECAY_RATE = "decay_rate"       # 衰减速率
    SENSITIVITY = "sensitivity"     # 敏感度
    WEIGHT = "weight"               # 子维度聚合权重
    VALUE_OFFSET = "value_offset"   # 当前值偏移（直接加减）


class BuffScope(str, Enum):
    """buff 作用范围"""
    DIMENSION = "dimension"           # 作用于顶层维度
    SUB_DIMENSION = "sub_dimension"   # 作用于子维度


class BuffDuration(str, Enum):
    """buff 持续类型"""
    TEMPORARY = "temporary"   # 临时：有明确 tick 数
    LONG_TERM = "long_term"   # 长期：场景级别（几天~几周）
    PERMANENT = "permanent"   # 永久：角色终身特质


class Buff(BaseModel):
    """
    修正器（buff/debuff 统称）。
    对维度或子维度的任意属性施加修正。
    不评价好坏——性瘾是buff，维生素缺乏也是buff。
    """
    id: str = Field(description="唯一标识，如 'iron_deficiency', 'adrenaline_rush'")
    name: str = Field(description="显示名，如 '缺铁性贫血', '肾上腺素飙升'")
    description: str = Field(default="", description="详细描述")

    # 作用目标
    scope: BuffScope = Field(description="作用于维度还是子维度")
    dimension: int = Field(ge=0, le=19, description="目标维度索引(0-19)")
    sub_name: str = Field(default="", description="子维度名（scope=SUB_DIMENSION时必填）")

    # 修正内容
    target: BuffTarget = Field(description="修正哪个属性")
    modifier: float = Field(description="修正值：叠加模式（+0.1 表示加0.1，×1.5 表示乘1.5）")
    is_multiplicative: bool = Field(default=False, description="True=乘法修正，False=加法修正")

    # 持续时间
    duration: BuffDuration = Field(default=BuffDuration.PERMANENT)
    remaining_ticks: int = Field(default=-1, description="剩余tick数（-1=永久/长期）")

    # 元信息
    source: str = Field(default="", description="来源：'genetic', 'disease', 'drug', 'environment' 等")
    stacks: int = Field(default=1, ge=1, description="叠加层数")


class DimensionConfig(BaseModel):
    """单个维度的个性化配置"""
    baseline: float = Field(ge=-1.0, le=1.0, description="基线值，角色的默认状态")
    sensitivity: float = Field(ge=0.0, le=5.0, description="敏感度，事件作用倍率")
    decay_rate: float = Field(ge=0.0, le=1.0, description="回归速率，偏离基线后多快回归，0=不回归，1=瞬间回归")
    sub_dimensions: dict[str, SubDimension] = Field(
        default_factory=dict,
        description="子维度（可选），聚合后覆盖顶层value"
    )
    buffs: list[Buff] = Field(
        default_factory=list,
        description="生效中的修正器列表"
    )


class CharacterVector(BaseModel):
    """角色的本我层 - 20维状态向量"""
    
    # 20个当前值
    values: list[float] = Field(
        min_length=20, max_length=20,
        description="20个维度的当前值，范围[-1.0, 1.0]"
    )
    
    # 20个个性化配置
    configs: list[DimensionConfig] = Field(
        min_length=20, max_length=20,
        description="20个维度的个性化配置"
    )
    
    def get_value(self, dim: Dimension) -> float:
        return self.values[dim.value]
    
    def set_value(self, dim: Dimension, value: float) -> None:
        self.values[dim.value] = max(-1.0, min(1.0, value))
    
    def apply_event_impact(self, dim: Dimension, raw_delta: float) -> float:
        """应用事件影响：原始delta × 有效敏感度 = 实际偏移，返回实际偏移量"""
        sensitivity = self.get_effective_sensitivity(dim)
        actual_delta = raw_delta * sensitivity
        old_value = self.get_value(dim)
        new_value = max(-1.0, min(1.0, old_value + actual_delta))
        self.set_value(dim, new_value)
        return new_value - old_value
    
    def decay_all(self, dt: float = 1.0) -> None:
        """时间衰减：所有维度向有效基线回归，子维度独立衰减后聚合到顶层。推进buff计时器。"""
        # 推进buff计时器
        self.tick_buffs()

        # 顶层维度衰减（使用effective值）
        for i in range(20):
            dim = Dimension(i)
            config = self.configs[i]
            # 有子维度的维度跳过顶层衰减，由子维度聚合接管
            if config.sub_dimensions:
                continue
            effective_decay = self.get_effective_decay_rate(dim)
            if effective_decay <= 0:
                continue
            current = self.values[i]
            effective_baseline = self.get_effective_baseline(dim)
            diff = effective_baseline - current
            regression = diff * effective_decay * dt
            self.values[i] = max(-1.0, min(1.0, current + regression))

        # 子维度独立衰减 + 聚合
        for i in range(20):
            dim = Dimension(i)
            config = self.configs[i]
            if not config.sub_dimensions:
                continue
            # 每个子维度独立衰减（使用buff修正后的值）
            for name, sub in config.sub_dimensions.items():
                eff_decay = self.get_sub_effective_decay(dim, name)
                if eff_decay <= 0:
                    continue
                eff_baseline = self.get_sub_effective_baseline(dim, name)
                diff = eff_baseline - sub.value
                sub.value = max(-1.0, min(1.0, sub.value + diff * eff_decay * dt))
            # 加权平均聚合到顶层
            total_weight = sum(s.weight for s in config.sub_dimensions.values())
            if total_weight > 0:
                aggregated = sum(s.value * s.weight for s in config.sub_dimensions.values()) / total_weight
                self.values[i] = max(-1.0, min(1.0, aggregated))

    # ============================================================
    #  子维度操作接口
    # ============================================================

    def get_sub_value(self, dim: Dimension, sub_name: str) -> float | None:
        """获取子维度当前值，无子维度返回None"""
        subs = self.configs[dim.value].sub_dimensions
        return subs[sub_name].value if sub_name in subs else None

    def set_sub_value(self, dim: Dimension, sub_name: str, value: float) -> bool:
        """设置子维度值并重新聚合，返回是否成功"""
        subs = self.configs[dim.value].sub_dimensions
        if sub_name not in subs:
            return False
        subs[sub_name].value = max(-1.0, min(1.0, value))
        # 重新聚合
        total_weight = sum(s.weight for s in subs.values())
        if total_weight > 0:
            aggregated = sum(s.value * s.weight for s in subs.values()) / total_weight
            self.values[dim.value] = max(-1.0, min(1.0, aggregated))
        return True

    def apply_sub_impact(self, dim: Dimension, sub_name: str, delta: float) -> float:
        """对子维度施加影响（如吃东西 → food+0.3），自动聚合到顶层"""
        subs = self.configs[dim.value].sub_dimensions
        if sub_name not in subs:
            return 0.0
        old = subs[sub_name].value
        subs[sub_name].value = max(-1.0, min(1.0, old + delta))
        # 重新聚合
        total_weight = sum(s.weight for s in subs.values())
        if total_weight > 0:
            aggregated = sum(s.value * s.weight for s in subs.values()) / total_weight
            self.values[dim.value] = max(-1.0, min(1.0, aggregated))
        return subs[sub_name].value - old

    def get_sub_summary(self, dim: Dimension) -> dict[str, float]:
        """获取某维度所有子维度的值"""
        subs = self.configs[dim.value].sub_dimensions
        return {name: round(s.value, 3) for name, s in subs.items()}

    # ============================================================
    #  Buff 系统（修正器管理）
    # ============================================================

    def add_buff(self, buff: Buff) -> None:
        """添加一个buff。同id的buff默认叠加层数"""
        config = self.configs[buff.dimension]
        # 查找同id已有buff
        existing = next((b for b in config.buffs if b.id == buff.id), None)
        if existing:
            existing.stacks += 1
        else:
            config.buffs.append(buff)

    def remove_buff(self, buff_id: str, dimension: int | None = None) -> bool:
        """移除指定id的buff，可限定维度。返回是否找到并移除"""
        dims_to_check = [dimension] if dimension is not None else range(20)
        for i in dims_to_check:
            config = self.configs[i]
            for j, b in enumerate(config.buffs):
                if b.id == buff_id:
                    config.buffs.pop(j)
                    return True
        return False

    def tick_buffs(self) -> list[str]:
        """
        推进所有临时buff的计时器。
        返回本tick过期的buff id列表。
        """
        expired = []
        for i in range(20):
            config = self.configs[i]
            to_remove = []
            for j, buff in enumerate(config.buffs):
                if buff.duration == BuffDuration.TEMPORARY and buff.remaining_ticks > 0:
                    buff.remaining_ticks -= 1
                    if buff.remaining_ticks <= 0:
                        expired.append(buff.id)
                        to_remove.append(j)
            for j in reversed(to_remove):
                config.buffs.pop(j)
        return expired

    def get_effective_baseline(self, dim: Dimension) -> float:
        """获取维度经过buff修正后的有效基线"""
        base = self.configs[dim.value].baseline
        return self._apply_buff_modifiers(dim.value, BuffTarget.BASELINE, base)

    def get_effective_sensitivity(self, dim: Dimension) -> float:
        """获取维度经过buff修正后的有效敏感度"""
        base = self.configs[dim.value].sensitivity
        return self._apply_buff_modifiers(dim.value, BuffTarget.SENSITIVITY, base)

    def get_effective_decay_rate(self, dim: Dimension) -> float:
        """获取维度经过buff修正后的有效衰减速率"""
        base = self.configs[dim.value].decay_rate
        return self._apply_buff_modifiers(dim.value, BuffTarget.DECAY_RATE, base)

    def get_sub_effective_decay(self, dim: Dimension, sub_name: str) -> float:
        """获取子维度经过buff修正后的有效衰减速率"""
        sub = self.configs[dim.value].sub_dimensions.get(sub_name)
        if not sub:
            return 0.0
        base = sub.decay_rate
        # 只找作用于该子维度的buff
        for buff in self.configs[dim.value].buffs:
            if (buff.scope == BuffScope.SUB_DIMENSION
                and buff.sub_name == sub_name
                and buff.target == BuffTarget.DECAY_RATE):
                mod = buff.modifier * buff.stacks
                if buff.is_multiplicative:
                    base *= mod
                else:
                    base += mod
        return max(0.0, base)

    def get_sub_effective_baseline(self, dim: Dimension, sub_name: str) -> float:
        """获取子维度经过buff修正后的有效基线"""
        sub = self.configs[dim.value].sub_dimensions.get(sub_name)
        if not sub:
            return 0.0
        base = sub.baseline
        for buff in self.configs[dim.value].buffs:
            if (buff.scope == BuffScope.SUB_DIMENSION
                and buff.sub_name == sub_name
                and buff.target == BuffTarget.BASELINE):
                mod = buff.modifier * buff.stacks
                if buff.is_multiplicative:
                    base *= mod
                else:
                    base += mod
        return max(-1.0, min(1.0, base))

    def get_all_buffs(self) -> list[tuple[int, Buff]]:
        """返回所有生效中的buff，附带维度索引"""
        result = []
        for i in range(20):
            for buff in self.configs[i].buffs:
                result.append((i, buff))
        return result

    def get_buff_description(self) -> list[str]:
        """返回所有buff的人类可读描述列表"""
        lines = []
        for i, buff in self.get_all_buffs():
            dim_name = DIMENSION_NAMES[Dimension(i)][0]
            duration_str = {
                BuffDuration.TEMPORARY: f"剩余{buff.remaining_ticks}tick",
                BuffDuration.LONG_TERM: "长期",
                BuffDuration.PERMANENT: "永久",
            }[buff.duration]
            stacks_str = f"×{buff.stacks}" if buff.stacks > 1 else ""
            lines.append(f"  {buff.name}{stacks_str} → {dim_name} {buff.target.value} ({duration_str})")
        return lines

    def _apply_buff_modifiers(self, dim_idx: int, target: BuffTarget, base_value: float) -> float:
        """内部：对维度级属性应用所有匹配buff的修正"""
        for buff in self.configs[dim_idx].buffs:
            if buff.scope == BuffScope.DIMENSION and buff.target == target:
                mod = buff.modifier * buff.stacks
                if buff.is_multiplicative:
                    base_value *= mod
                else:
                    base_value += mod
        # clamp到合理范围
        if target == BuffTarget.SENSITIVITY:
            return max(0.0, base_value)
        elif target == BuffTarget.DECAY_RATE:
            return max(0.0, min(1.0, base_value))
        else:
            return max(-1.0, min(1.0, base_value))
    
    def get_deviation(self, dim: Dimension) -> float:
        """获取某维度偏离基线的程度"""
        return self.values[dim.value] - self.configs[dim.value].baseline
    
    def summary(self) -> dict[str, float]:
        """返回维度名→当前值的字典"""
        return {
            DIMENSION_NAMES[Dimension(i)][1]: round(self.values[i], 3)
            for i in range(20)
        }
    
    def dominant_traits(self, threshold: float = 0.3) -> list[tuple[str, float]]:
        """返回偏离基线最大的维度"""
        deviations = []
        for i in range(20):
            dev = abs(self.values[i] - self.configs[i].baseline)
            if dev >= threshold:
                name = DIMENSION_NAMES[Dimension(i)][1]
                deviations.append((name, round(self.values[i], 3)))
        deviations.sort(key=lambda x: abs(x[1]), reverse=True)
        return deviations
    
    @classmethod
    def create(
        cls,
        initial_values: list[float],
        baselines: list[float] | None = None,
        sensitivities: list[float] | None = None,
        decay_rates: list[float] | None = None,
    ) -> "CharacterVector":
        """便捷构造方法。
        
        initial_values: 20维初始值（角色进场时的当前状态）
        baselines: 20维基线值（衰减回归目标，角色的"满血状态"）。
            性格驱动器(0-9)默认=初始值（人格不轻易变）
            生理驱动器(10-19)按类型：
              恢复型(VITALITY,SECURITY) → 偏正(0.3)
              消耗型(SATIATION) → 0
              性格型(DESIRE_UNDERSTANDING,ATTACHMENT) → =初始值
              即时型(其余) → 0
            角色可自由配置全部20维baseline。
        """
        if baselines is None:
            baselines = (
                initial_values[:10]                  # 性格0-9: 基线=初始值
                + [0.3]                              # 10 VITALITY: 恢复型
                + [0.0]                              # 11 SATIATION: 消耗型
                + [0.3]                              # 12 SECURITY: 恢复型
                + [0.0]                              # 13 COMFORT: 即时型
                + [0.0]                              # 14 LIBIDO: 即时型
                + [initial_values[15]]               # 15 DESIRE_UNDERSTANDING: 性格型
                + [0.0]                              # 16 SHAME: 即时型
                + [0.0]                              # 17 SENSORY_PLEASURE: 即时型
                + [initial_values[18]]               # 18 ATTACHMENT: 性格型
                + [0.0]                              # 19 RELEASE_IMPULSE: 即时型
            )
        if sensitivities is None:
            sensitivities = [1.0] * 20
        if decay_rates is None:
            # 性格驱动器默认慢回归，生理驱动器默认中速回归
            decay_rates = [0.05] * 10 + [0.1] * 10
        
        configs = [
            DimensionConfig(
                baseline=baselines[i],
                sensitivity=sensitivities[i],
                decay_rate=decay_rates[i],
            )
            for i in range(20)
        ]
        return cls(values=initial_values, configs=configs)
