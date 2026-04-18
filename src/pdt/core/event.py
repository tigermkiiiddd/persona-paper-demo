"""
事件结构体 - 外界信息的统一输入格式

所有外界交互（人/物/场景/环境变化）都统一为事件结构体。
"""

from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """事件类型"""
    INTERPERSONAL = "interpersonal"  # 人际交互
    ENVIRONMENT = "environment"      # 环境变化
    BODY = "body"                    # 身体状态
    INFORMATION = "information"      # 信息获取
    SCENE = "scene"                  # 场景切换


class Valence(str, Enum):
    """效价 - 事件对角色的倾向"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class Duration(str, Enum):
    """持续性"""
    INSTANT = "instant"          # 一次性冲击
    SUSTAINED = "sustained"      # 持续状态
    INSTANT_PLUS_SUSTAINED = "instant+sustained"  # 即时冲击+后续持续


class Event(BaseModel):
    """外界信息结构体"""
    event_type: EventType = Field(description="事件分类")
    intensity: float = Field(ge=0.0, le=1.0, description="冲击力量化值 0.0-1.0")
    source: str = Field(description="来源，不限类型（人/物/自然/时间/未知/组合）")
    content: str = Field(description="具体事件描述")
    valence: Valence = Field(description="对角色的倾向")
    duration: Duration = Field(description="持续性")


# 维度影响映射：事件效价+类型 → 哪些维度受影响、方向和权重
# key = (event_type, valence), value = list of (dimension_index, direction, weight)
# direction: -1 = 负向影响（降低）, +1 = 正向影响（升高）
# weight: 基础权重，最终偏移 = intensity × weight × direction × sensitivity

EVENT_IMPACT_RULES: dict[tuple[EventType, Valence], list[tuple[int, int, float]]] = {
    # 人际 + 负面：被攻击、被羞辱、被背叛等
    (EventType.INTERPERSONAL, Valence.NEGATIVE): [
        (12, -1, 0.8),  # 安全感↓
        (1, -1, 0.3),   # 亲和度↓
        (6, -1, 0.2),   # 自尊心↓
        (19, 1, 0.4),   # 释放冲动↑
        (16, 1, 0.2),   # 羞耻感↑
    ],
    # 人际 + 正面：被夸奖、被帮助、被爱等
    (EventType.INTERPERSONAL, Valence.POSITIVE): [
        (12, 1, 0.3),   # 安全感↑
        (1, 1, 0.4),    # 亲和度↑
        (6, 1, 0.3),    # 自尊心↑
        (18, 1, 0.3),   # 依恋需求↑
        (13, 1, 0.2),   # 舒适度↑
    ],
    # 人际 + 中性：普通交流、问路等
    (EventType.INTERPERSONAL, Valence.NEUTRAL): [
        (5, 1, 0.1),    # 好奇心微↑
    ],
    # 环境 + 负面：灾害、恶劣天气、危险环境
    (EventType.ENVIRONMENT, Valence.NEGATIVE): [
        (12, -1, 0.7),  # 安全感↓
        (13, -1, 0.5),  # 舒适度↓
        (10, -1, 0.2),  # 生命力↓
        (19, 1, 0.3),   # 释放冲动↑
    ],
    # 环境 + 正面：好天气、舒适环境
    (EventType.ENVIRONMENT, Valence.POSITIVE): [
        (13, 1, 0.4),   # 舒适度↑
        (12, 1, 0.2),   # 安全感↑
        (17, 1, 0.2),   # 感官愉悦↑
    ],
    # 身体 + 负面：受伤、生病、疲劳
    (EventType.BODY, Valence.NEGATIVE): [
        (10, -1, 0.6),  # 生命力↓
        (13, -1, 0.5),  # 舒适度↓
        (12, -1, 0.3),  # 安全感↓
        (4, 1, 0.3),    # 情绪波动↑
    ],
    # 身体 + 正面：休息好了、吃饱了
    (EventType.BODY, Valence.POSITIVE): [
        (10, 1, 0.4),   # 生命力↑
        (13, 1, 0.5),   # 舒适度↑
        (11, 1, 0.6),   # 饥饿满足↑
    ],
    # 信息 + 负面：坏消息、谣言、威胁
    (EventType.INFORMATION, Valence.NEGATIVE): [
        (12, -1, 0.4),  # 安全感↓
        (6, -1, 0.2),   # 自尊心↓
        (4, 1, 0.3),    # 情绪波动↑
    ],
    # 信息 + 正面：好消息、学到新知识
    (EventType.INFORMATION, Valence.POSITIVE): [
        (5, 1, 0.3),    # 好奇心↑
        (6, 1, 0.2),    # 自尊心↑
    ],
    # 信息 + 中性
    (EventType.INFORMATION, Valence.NEUTRAL): [
        (5, 1, 0.2),    # 好奇心↑
    ],
    # 场景 + 负面：被传送到危险地方
    (EventType.SCENE, Valence.NEGATIVE): [
        (12, -1, 0.6),  # 安全感↓
        (5, 1, 0.3),    # 好奇心↑（新环境）
    ],
    # 场景 + 中性：到达新地方
    (EventType.SCENE, Valence.NEUTRAL): [
        (5, 1, 0.4),    # 好奇心↑
    ],
}
