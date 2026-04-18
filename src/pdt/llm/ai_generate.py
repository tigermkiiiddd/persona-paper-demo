"""
AI 辅助角色生成 — tool calling 方式
"""

import os
from pathlib import Path
from typing import Any

# 加载项目 .env
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from openai import OpenAI

# ── 环境配置 ──────────────────────────────────────────────────

_api_key = os.getenv("OPENAI_API_KEY", "")
_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
_model = os.getenv("PDT_MODEL", "deepseek-chat")

_client = OpenAI(api_key=_api_key, base_url=_base_url) if _api_key else None

# ── 20 维完整语义描述 ────────────────────────────────────────

DIMENSION_SPECS = [
    {"index": 0, "cn": "掌控欲", "en": "Dominance", "range": "[-1,1]",
     "neg": "完全顺从，听从他人安排", "pos": "绝对主导，必须掌控一切",
     "note": "不等于领导能力，是\"想要控制\"的欲望，不是\"能够控制\"的能力"},

    {"index": 1, "cn": "亲和度", "en": "Affection", "range": "[-1,1]",
     "neg": "极端敌意，默认对所有人抱有敌意和不信任", "pos": "极致友好，默认信任和善待所有人",
     "note": "是内在倾向，不是外在表现。低亲和的人可以伪装友好，但内心不友好"},

    {"index": 2, "cn": "独立性", "en": "Independence", "range": "[-1,1]",
     "neg": "完全依赖，无法独自做决定", "pos": "绝对自主，排斥一切外部帮助和意见",
     "note": "高独立不等于高能力，是\"不需要别人\"的心态"},

    {"index": 3, "cn": "务实性", "en": "Pragmatism", "range": "[-1,1]",
     "neg": "完全感性，凭直觉和情感做判断", "pos": "绝对理性，一切以逻辑和事实为依据",
     "note": "不是\"对错\"的衡量，是思维方式的偏向。感性不等于错误，理性不等于正确"},

    {"index": 4, "cn": "情绪波动", "en": "Volatility", "range": "[-1,1]",
     "neg": "情绪极度稳定，几乎不受外界影响", "pos": "极度易变，一点小事就情绪剧烈波动",
     "note": "这不是具体的情绪，而是\"情绪容不容易变\"这个元属性"},

    {"index": 5, "cn": "好奇心", "en": "Curiosity", "range": "[-1,1]",
     "neg": "完全封闭，对新事物毫无兴趣甚至排斥", "pos": "极致探索，对一切未知都充满好奇",
     "note": "驱动探索行为和主动获取信息，低好奇心的人不会主动了解新事物"},

    {"index": 6, "cn": "自尊心", "en": "Self-Esteem", "range": "[-1,1]",
     "neg": "极度自卑，认为自己毫无价值", "pos": "极致自信，认为自己极其优秀",
     "note": "高自尊被羞辱照样会羞耻——自尊≠羞耻感的反面"},

    {"index": 7, "cn": "风险承受", "en": "Risk-Tolerance", "range": "[-1,1]",
     "neg": "完全规避，拒绝一切有风险的选择", "pos": "极致冒险，主动追求高风险高回报",
     "note": "不等于勇气。高风险承受的人可能只是不在乎后果"},

    {"index": 8, "cn": "同理心", "en": "Empathy", "range": "[-1,1]",
     "neg": "完全冷酷，无法或不愿感知他人感受", "pos": "极致共情，能深度感受他人的喜怒哀乐",
     "note": "是感知能力，不是行为。高同理心不等于善良（可能感知到了但不在乎）"},

    {"index": 9, "cn": "道德准则", "en": "Moral-Alignment", "range": "[-1,1]",
     "neg": "完全机会主义，为达目的不择手段", "pos": "极致坚守，宁可吃亏也不违背原则",
     "note": "不定义具体的道德内容，只描述\"有多在意原则\"这个程度"},

    # ── 生理/欲望驱动器 ──
    {"index": 10, "cn": "生命力", "en": "Vitality", "range": "[0,1]",
     "neg": "濒死/枯竭，没有力气做任何事", "pos": "巅峰活力，精力充沛",
     "note": "影响行动能力和主动性。低生命力的人不想动、不想社交、不想探索",
     "sub_dims": ["stamina", "mental", "sleep_debt"]},

    {"index": 11, "cn": "饥饿/满足", "en": "Satiation", "range": "[0,1]",
     "neg": "极度饥渴，生理需求紧急", "pos": "完全满足，没有任何饥渴感",
     "note": "这是\"满足度\"不是\"饥饿度\"。值越低越饿。随时间自然衰减",
     "sub_dims": ["food", "water", "electrolyte", "vitamin"]},

    {"index": 12, "cn": "安全感", "en": "Security", "range": "[0,1]",
     "neg": "极度恐惧，感觉随时有生命危险", "pos": "完全安心，没有任何威胁感",
     "note": "比舒适度更底层。安全感是\"会不会死\"级别，舒适度是\"过得爽不爽\"级别",
     "sub_dims": ["physical_threat", "social_threat", "existential"]},

    {"index": 13, "cn": "舒适度", "en": "Comfort", "range": "[0,1]",
     "neg": "极度不适，环境恶劣", "pos": "完全舒适，环境宜人",
     "note": "和安全感不同：躺豪华酒店可能很舒适但极度不安全",
     "sub_dims": ["temperature", "posture", "environment"]},

    {"index": 14, "cn": "性冲动", "en": "Libido", "range": "[0,1]",
     "neg": "完全排斥，对性毫无兴趣甚至厌恶", "pos": "极致渴望，性需求强烈",
     "note": "是内驱力，不是行为。高性冲动不等于会实施性行为（道德准则可能压制）"},

    {"index": 15, "cn": "渴望被理解", "en": "Desire-Understanding", "range": "[0,1]",
     "neg": "完全封闭，不在乎是否有人理解自己", "pos": "极致渴望，极度需要被理解",
     "note": "不同于依恋需求。依恋是\"需要你在身边\"，渴望被理解是\"需要你懂我\""},

    {"index": 16, "cn": "羞耻感", "en": "Shame", "range": "[0,1]",
     "neg": "完全无耻，做任何事都不会感到羞耻", "pos": "极致羞耻，极易感到丢脸和羞愧",
     "note": "和自尊心独立。高自尊的人也可能高羞耻（自信但怕丢脸）"},

    {"index": 17, "cn": "感官愉悦", "en": "Sensory-Pleasure", "range": "[0,1]",
     "neg": "完全麻木，对感官体验毫无感觉", "pos": "极致愉悦，极度追求美食、音乐等感官享受",
     "note": "不同于舒适度。感官愉悦是多巴胺级别的（美食、音乐），舒适度是环境级别的"},

    {"index": 18, "cn": "依恋需求", "en": "Attachment", "range": "[0,1]",
     "neg": "完全疏离，不需要任何人的情感陪伴", "pos": "极致依恋，无法忍受独处",
     "note": "和渴望被理解不同。依恋是\"需要你在身边\"，渴望被理解是\"需要你懂我\""},

    {"index": 19, "cn": "释放冲动", "en": "Release-Impulse", "range": "[0,1]",
     "neg": "完全压抑，绝对不会做出任何过激行为", "pos": "极致宣泄，极易爆发、动手、大吼",
     "note": "是行为层面，不是情绪层面。情绪波动是内部状态（稳不稳），释放冲动是外部行为（做不做过激的事）"},
]

# ── Tool schema ───────────────────────────────────────────────

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_character",
        "description": "根据用户的角色描述，生成完整的人格演绎剧场角色配置",
        "parameters": {
            "type": "object",
            "required": ["name", "dimensions", "appearance", "world_view", "personal_values"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "角色名"
                },
                "dimensions": {
                    "type": "array",
                    "description": "20个维度配置，每个维度是一个四元组 [初始值, 基线, 敏感度, 衰减速率]。性格维度范围[-1,1]，生理维度范围[0,1]。基线=衰减回归目标。敏感度0-5。衰减速率0-1。",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "minItems": 20,
                    "maxItems": 20,
                },
                "sub_dimensions": {
                    "type": "object",
                    "description": "子维度配置。key是维度index(字符串)。部分生理维度有子维度（10生命力,11饥饿,12安全感,13舒适度），每个子维度有name/value/baseline/decay_rate/weight。",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "value", "baseline", "decay_rate", "weight"],
                            "properties": {
                                "name": {"type": "string", "description": "子维度名"},
                                "value": {"type": "number", "description": "初始值 [0,1]"},
                                "baseline": {"type": "number", "description": "基线/衰减目标"},
                                "decay_rate": {"type": "number", "description": "衰减速率 0-1"},
                                "weight": {"type": "number", "description": "在父维度中的权重 0-1，系统会自动归一化，无需确保和为1"},
                            }
                        }
                    }
                },
                "appearance": {
                    "type": "object",
                    "description": "角色外观",
                    "properties": {
                        "height": {"type": "string", "description": "身高"},
                        "weight": {"type": "string", "description": "体重"},
                        "measurements": {"type": "string", "description": "三围"},
                        "hair": {"type": "string", "description": "发型/发色"},
                        "eyes": {"type": "string", "description": "瞳色"},
                        "skin": {"type": "string", "description": "肤色"},
                        "distinguishing_features": {"type": "string", "description": "显著特征(疤痕/纹身等)"},
                        "clothing": {"type": "string", "description": "当前穿着"},
                        "equipment": {"type": "string", "description": "装备/物品"},
                        "appearance_summary": {"type": "string", "description": "综合外观描述"},
                    }
                },
                "world_view": {"type": "string", "description": "世界观"},
                "personal_values": {"type": "string", "description": "价值观"},
                "love_view": {"type": "string", "description": "爱情观"},
                "culture": {"type": "string", "description": "文化背景"},
                "trauma": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "创伤/执念列表"
                },
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "技能列表"
                },
                "long_term_goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "长期目标"
                },
                "interruption_threshold": {
                    "type": "number",
                    "description": "打断阈值 [0,1]，0=容易打断 1=很难打断"
                },
                "debug_mode": {
                    "type": "boolean",
                    "description": "调试模式(催眠态)"
                },
            },
        },
    },
}


def _build_system_prompt() -> str:
    """构建系统 prompt，包含完整的维度语义"""
    dim_lines = []
    for d in DIMENSION_SPECS:
        line = f"[{d['index']:2d}] {d['cn']} ({d['en']})  范围{d['range']}"
        line += f"\n     低={d['neg']}"
        line += f"\n     高={d['pos']}"
        line += f"\n     注意: {d['note']}"
        if "sub_dims" in d:
            line += f"\n     子维度: {', '.join(d['sub_dims'])}"
        dim_lines.append(line)

    dims_text = "\n".join(dim_lines)

    return f"""\
你是人格演绎剧场（Persona Deduction Theater）的角色设计师。
用户会给一段角色描述，你调用 create_character 工具生成角色配置。

## 关键概念

每个维度是一个四元组 [初始值, 基线, 敏感度, 衰减速率]：
- 初始值: 角色进场时的当前状态
- 基线(baseline): 衰减回归目标，角色的"满血状态"
  - SATIATION baseline=0 → 自然变饿（消耗型）
  - VITALITY baseline=0.3 → 最多恢复到30%（如病人）
  - 修仙者 SATIATION baseline=1.0 → 辟谷不饿
- 敏感度: 对外界刺激的反应强度（0=麻木, 5=极度敏感，默认1）
- 衰减速率: 自然变化快慢（0=不变, 1=极速衰减）
  - 性格维度通常慢（0.01-0.02）
  - 生理维度通常快（0.03-0.08）

子维度: 部分生理维度有子维度树。子维度独立衰减，加权聚合到父维度。
父维度如果有子维度，其自身 decay_rate 应为 0（由子维度驱动衰减）。
子维度权重之和必须 = 1.0。

## 20 维完整语义

{dims_text}
"""


def ai_generate_character(description: str) -> dict:
    """
    用 tool calling 生成角色配置。
    返回前端可用的完整角色数据。
    """
    if not _client:
        raise RuntimeError(
            "未配置 OPENAI_API_KEY，无法使用 AI 生成。请在 .env 中设置。"
        )

    resp = _client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": description},
        ],
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "create_character"}},
        temperature=0.8,
        max_tokens=3000,
    )

    # 提取 tool call 参数
    msg = resp.choices[0].message
    if not msg.tool_calls:
        raise ValueError("AI 未调用 create_character 工具，请重试")

    import json
    tool_call = msg.tool_calls[0]
    data = json.loads(tool_call.function.arguments)

    # 展开四元组为前端需要的平铺数组
    dims = data.get("dimensions", [])
    if len(dims) != 20:
        # 尝试补齐或截断
        while len(dims) < 20:
            dims.append([0.0, 0.0, 1.0, 0.02])
        dims = dims[:20]

    values = [d[0] for d in dims]
    baselines = [d[1] for d in dims]
    sensitivities = [d[2] for d in dims]
    decay_rates = [d[3] for d in dims]

    # 默认外观字段补全
    default_app = {
        "height": "", "weight": "", "measurements": "",
        "hair": "", "eyes": "", "skin": "",
        "distinguishing_features": "", "clothing": "",
        "equipment": "", "appearance_summary": "",
    }
    app = data.get("appearance", {})
    merged_app = {**default_app, **{k: v for k, v in app.items() if k in default_app}}

    # 列表字段
    for key in ("trauma", "skills", "long_term_goals"):
        val = data.get(key, [])
        if isinstance(val, str):
            val = [val]
        data[key] = val

    # 归一化子维度权重：weight / sum(weights)
    raw_subs = data.get("sub_dimensions", {})
    normalized_subs = {}
    for dim_key, subs in raw_subs.items():
        if not subs:
            continue
        total_w = sum(s.get("weight", 0.5) for s in subs)
        if total_w <= 0:
            total_w = 1.0
        normalized_subs[dim_key] = [
            {**s, "weight": s.get("weight", 0.5) / total_w} for s in subs
        ]

    # 构造前端 CharacterCreateRequest 兼容的结构
    result = {
        "name": data.get("name", "未命名角色"),
        "values": values,
        "baselines": baselines,
        "sensitivities": sensitivities,
        "decay_rates": decay_rates,
        "sub_dimensions": normalized_subs,
        "buffs": [],
        "appearance": merged_app,
        "world_view": data.get("world_view", ""),
        "personal_values": data.get("personal_values", ""),
        "love_view": data.get("love_view", ""),
        "culture": data.get("culture", ""),
        "trauma": data.get("trauma", []),
        "skills": data.get("skills", []),
        "long_term_goals": data.get("long_term_goals", []),
        "interruption_threshold": data.get("interruption_threshold", 0.5),
        "position_x": 0.0,
        "position_y": 0.0,
        "debug_mode": data.get("debug_mode", False),
    }

    return result
