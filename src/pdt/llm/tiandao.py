"""
天道 LLM 法则生成 — 当角色做出 CUSTOM 行为时，天道系统介入

流程：
1. 收集行为描述 + 世界上下文
2. LLM 生成一条世界法则（WorldRule）
3. 法则注册到 RuleRegistry（带 tiandao 标记）
4. 用新法则判定这次行为
5. 法则持久化，后续同类行为直接命中规则
"""

import json
import uuid
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional

from ..core.behavior import BehaviorAction, ActionType, JudgeResult
from ..engine.judge import WorldRule, WorldState, RuleSource, RuleRegistry


TIANDAO_SYSTEM_PROMPT = """你是「人格推演沙盘」的天道系统——世界法则的制定者。

你的职责：当角色做出【自定义行为】（不属于移动/攻击/交互/社交等标准类型）时，
你需要即时生成一条世界法则来判定这个行为的结果。

## 法则格式

返回 JSON，包含：
- name: 法则名（简短，如"隔空取物"、"轻功"、"毒术"）
- description: 自然语言描述（这条法则管什么）
- precondition: 前置条件（什么情况下适用）
- formula: 数值计算公式（自然语言，如"成功率 = 灵敏度 × 0.5 + 修炼程度 × 0.3"）
- effects: 效果列表（成功会怎样）
- failure_effects: 失败效果（失败会怎样）
- confidence: 可信度 0.0-1.0（越离谱越低）

## 判定原则

1. **合理优先**: 符合物理常识和场景设定的行为 confidence 高
2. **能量守恒**: 越强大的效果需要越高的代价（消耗HP/体力/维度偏移）
3. **能力挂钩**: 判定公式要引用角色的身体素质或维度值
4. **失败有代价**: 失败不应该是"没事"，应该有代价（受伤/疲劳/尴尬）
5. **一致性**: 同类行为应产生相似的法则

## 上下文

{context}
"""


class TiandaoResult(BaseModel):
    """天道判定结果"""
    rule: WorldRule
    judge_result: JudgeResult


class TiandaoSystem:
    """
    天道法则生成系统

    当 JudgeSystem 遇到 CUSTOM 行为时调用。
    LLM 生成法则 → 注册到 RuleRegistry → 用法则判定。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4",
        rule_registry: Optional[RuleRegistry] = None,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.rule_registry = rule_registry or RuleRegistry()

    def judge_custom(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> TiandaoResult:
        """
        对 CUSTOM 行为进行天道判定

        1. 构建上下文 prompt
        2. LLM 生成法则
        3. 注册法则
        4. 根据法则生成判定结果
        """
        # 构建上下文
        context = self._build_context(action, actor_name, ws)
        prompt = TIANDAO_SYSTEM_PROMPT.format(context=context)

        # 获取角色身体素质
        physique = ws.get_physique(actor_name)

        user_msg = (
            f"角色【{actor_name}】做出自定义行为：\n"
            f"行为描述: {action.custom_description or action.description}\n"
            f"持续时长: {action.duration}分钟\n"
            f"角色身体素质: {physique.model_dump_json(indent=2)}\n"
            f"当前位置: {ws.character_positions.get(actor_name, (0, 0))}\n"
            f"\n请生成一条世界法则来判定这个行为。返回JSON。"
        )

        # LLM 调用
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            timeout=30,
            response_format={"type": "json_object"},
        )

        # 解析法则
        try:
            rule_data = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            rule_data = {
                "name": "未知法则",
                "description": "天道无法理解的行为",
                "confidence": 0.1,
            }

        rule = WorldRule(
            rule_id=f"tiandao_{uuid.uuid4().hex[:8]}",
            name=rule_data.get("name", "未命名法则"),
            description=rule_data.get("description", ""),
            trigger_action_type=ActionType.CUSTOM,
            precondition=rule_data.get("precondition", ""),
            formula=rule_data.get("formula", ""),
            effects=rule_data.get("effects", []),
            source=RuleSource.TIANDAO,
            confidence=min(1.0, max(0.0, float(rule_data.get("confidence", 0.5)))),
        )

        # 注册法则
        self.rule_registry.register(rule)

        # 生成判定结果
        judge_result = self._apply_rule(rule, action, actor_name, ws, physique, rule_data)

        return TiandaoResult(rule=rule, judge_result=judge_result)

    def _build_context(
        self,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
    ) -> str:
        """构建世界上下文描述"""
        parts = []

        if ws.scene:
            parts.append(f"场景: {ws.scene.name if hasattr(ws.scene, 'name') else '未知'}")

        # 场上其他角色
        others = [name for name in ws.character_positions if name != actor_name]
        if others:
            parts.append(f"在场角色: {', '.join(others)}")

        # 目标
        if action.target_name:
            parts.append(f"目标角色: {action.target_name}")

        # 已有天道法则（供参考）
        tiandao_rules = [
            r for r in self.rule_registry.rules.values()
            if r.source == RuleSource.TIANDAO
        ]
        if tiandao_rules:
            rule_names = [f"{r.name}({r.confidence:.0%})" for r in tiandao_rules[-5:]]
            parts.append(f"近期天道法则: {', '.join(rule_names)}")

        return "\n".join(parts) if parts else "空旷场景，无特殊条件"

    def _apply_rule(
        self,
        rule: WorldRule,
        action: BehaviorAction,
        actor_name: str,
        ws: WorldState,
        physique,
        rule_data: dict,
    ) -> JudgeResult:
        """
        根据天道法则生成判定结果

        简化实现：用 confidence + 角色身体素质决定成功/失败
        后续可扩展为更复杂的判定公式解析
        """
        # 成功率 = 法则可信度 × 角色综合能力
        combat_ability = (physique.attack_power + physique.dodge_capability + physique.combat_perception) / 3
        success_threshold = rule.confidence * combat_ability

        # 简单阈值判定：综合能力够就成功
        success = success_threshold > 0.3

        if success:
            # 成功：效果由法则描述
            effects_desc = "；".join(rule.effects) if rule.effects else "行为成功"
            broadcast = f"{actor_name}{action.custom_description or action.description}——{rule.name}生效"

            # 计算代价（消耗体力）
            stamina_cost = action.duration * (1.0 - physique.stamina_efficiency) * 5

            return JudgeResult(
                action_type=ActionType.CUSTOM,
                success=True,
                reason=f"天道法则【{rule.name}】判定成功: {effects_desc}",
                broadcast_content=broadcast,
                broadcast_type="visual",
                broadcast_valence="positive",
            )
        else:
            # 失败：有代价
            failure_effects = rule_data.get("failure_effects", ["行为失败，白白消耗体力"])
            fail_desc = "；".join(failure_effects) if isinstance(failure_effects, list) else str(failure_effects)

            return JudgeResult(
                action_type=ActionType.CUSTOM,
                success=False,
                reason=f"天道法则【{rule.name}】判定失败: {fail_desc}",
                broadcast_content=f"{actor_name}试图{action.custom_description or action.description}，但失败了",
                broadcast_type="visual",
                broadcast_valence="negative",
            )
