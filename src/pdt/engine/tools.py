"""
工具注册表 — 角色的所有可用工具定义

分三类：
1. 外部行为：产生世界事件，其他角色能感知到
2. 内部修改：只改自己的内部状态，不广播
3. 物理效果：修改他人/环境的物理状态
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Any


class ToolCategory(str, Enum):
    EXTERNAL = "external"    # 外部行为，广播
    INTERNAL = "internal"    # 内部修改，不广播
    PHYSICAL = "physical"    # 物理效果，改别人状态


class ToolParam(BaseModel):
    """工具参数定义"""
    name: str
    type: str = "string"  # string, number, boolean
    description: str = ""
    required: bool = True
    enum: list[str] | None = None


class ToolDef(BaseModel):
    """工具定义"""
    name: str
    category: ToolCategory
    description: str
    parameters: list[ToolParam]
    # 执行后是否需要继续调用其他工具（工具链）
    returns_result: bool = Field(default=False, description="是否返回结果供后续工具使用")


# ============================================================
#  工具定义
# ============================================================

TOOLS: list[ToolDef] = [

    # ---- 外部行为 ----
    ToolDef(
        name="speak",
        category=ToolCategory.EXTERNAL,
        description="说话。其他人能听到。",
        parameters=[
            ToolParam(name="content", type="string", description="说的话"),
            ToolParam(name="volume", type="string", description="音量", enum=["whisper", "normal", "loud", "shout"], required=False),
            ToolParam(name="target", type="string", description="对谁说（空=对所有人）", required=False),
        ],
    ),
    ToolDef(
        name="act",
        category=ToolCategory.EXTERNAL,
        description="身体动作。有持续时间。其他人能看到。可以不动（不调用此工具）。",
        parameters=[
            ToolParam(name="description", type="string", description="动作描述"),
            ToolParam(name="duration_seconds", type="number", description="持续时间（秒）", required=False),
            ToolParam(name="move_dx", type="number", description="X方向位移（米）", required=False),
            ToolParam(name="move_dy", type="number", description="Y方向位移（米）", required=False),
            ToolParam(name="target", type="string", description="动作对象", required=False),
        ],
    ),

    # ---- 内部修改 ----
    ToolDef(
        name="set_goal",
        category=ToolCategory.INTERNAL,
        description="设置或覆盖自己的短期目标。这是内部决策，其他人看不到。",
        parameters=[
            ToolParam(name="goal", type="string", description="新的短期目标"),
        ],
    ),
    ToolDef(
        name="think",
        category=ToolCategory.INTERNAL,
        description="内心想法和情绪认知。不外露。",
        parameters=[
            ToolParam(name="content", type="string", description="内心的想法"),
            ToolParam(name="emotion", type="string", description="当前情绪", required=False),
        ],
    ),
    ToolDef(
        name="feel",
        category=ToolCategory.INTERNAL,
        description="感受自己的身体状态变化。不外露。",
        parameters=[
            ToolParam(name="pain", type="number", description="疼痛 0-1", required=False),
            ToolParam(name="fatigue", type="number", description="疲劳 0-1", required=False),
            ToolParam(name="temperature", type="string", description="温度感: cold/cool/normal/warm/hot", required=False),
            ToolParam(name="custom", type="string", description="其他感受描述", required=False),
        ],
    ),

    # ---- 物理效果 ----
    ToolDef(
        name="attack",
        category=ToolCategory.PHYSICAL,
        description="攻击目标的某个身体部位。",
        parameters=[
            ToolParam(name="target", type="string", description="攻击对象的名字"),
            ToolParam(name="body_part", type="string", description="攻击部位: head/chest/back/left_arm/right_arm/left_hand/right_hand/left_leg/right_leg"),
            ToolParam(name="damage", type="number", description="伤害值"),
        ],
    ),
    ToolDef(
        name="bind",
        category=ToolCategory.PHYSICAL,
        description="绑住目标的某个肢体。",
        parameters=[
            ToolParam(name="target", type="string", description="目标名字"),
            ToolParam(name="limb", type="string", description="肢体名: left_hand/right_hand/left_arm/right_arm/left_leg/right_leg"),
            ToolParam(name="detail", type="string", description="怎么绑的", required=False),
        ],
    ),
    ToolDef(
        name="unbind",
        category=ToolCategory.PHYSICAL,
        description="解开目标被绑的肢体。",
        parameters=[
            ToolParam(name="target", type="string", description="目标名字"),
            ToolParam(name="limb", type="string", description="肢体名"),
        ],
    ),
    ToolDef(
        name="heal",
        category=ToolCategory.PHYSICAL,
        description="治疗目标的某个部位。",
        parameters=[
            ToolParam(name="target", type="string", description="目标名字"),
            ToolParam(name="body_part", type="string", description="治疗部位"),
            ToolParam(name="amount", type="number", description="治疗量"),
        ],
    ),
    ToolDef(
        name="push",
        category=ToolCategory.PHYSICAL,
        description="把目标往某方向推。",
        parameters=[
            ToolParam(name="target", type="string", description="目标名字"),
            ToolParam(name="direction", type="string", description="方向: north/south/east/west"),
            ToolParam(name="force", type="number", description="力度", required=False),
        ],
    ),
]


# ============================================================
#  工具查找
# ============================================================

_tool_map: dict[str, ToolDef] = {t.name: t for t in TOOLS}


def get_tool(name: str) -> ToolDef | None:
    return _tool_map.get(name)


def get_tools_by_category(category: ToolCategory) -> list[ToolDef]:
    return [t for t in TOOLS if t.category == category]


def all_tool_names() -> list[str]:
    return [t.name for t in TOOLS]


def tools_to_openai_format() -> list[dict]:
    """转为 OpenAI function calling 格式"""
    result = []
    for tool in TOOLS:
        properties = {}
        required = []
        for param in tool.parameters:
            prop: dict[str, Any] = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        result.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return result
