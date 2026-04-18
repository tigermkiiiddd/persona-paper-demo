"""
工具执行器 — 接收工具调用，在角色和世界上产生效果

每次工具调用返回 ToolResult：
- success: 是否成功
- message: 描述文字（LLM可见，用于工具链决策）
- world_events: 产生的世界事件（广播给其他角色）
"""

from pydantic import BaseModel, Field
from ..core.character import Character
from ..core.spatial import WorldEvent


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = True
    message: str = ""
    world_events: list[dict] = Field(default_factory=list, description="产生的世界事件 [{content, event_type}]")

    class Config:
        arbitrary_types_allowed = True


class ToolExecutor:
    """
    工具执行器。
    
    接收 (tool_name, args, caller, all_characters)，
    执行效果，返回 ToolResult。
    """

    def __init__(self, characters: list[Character]):
        self.character_map: dict[str, Character] = {c.name: c for c in characters}

    def execute(self, tool_name: str, args: dict, caller: Character) -> ToolResult:
        """执行一个工具调用"""
        handler = getattr(self, f"_exec_{tool_name}", None)
        if handler is None:
            return ToolResult(success=False, message=f"未知工具: {tool_name}")
        return handler(args, caller)

    # ============================================================
    #  外部行为
    # ============================================================

    def _exec_speak(self, args: dict, caller: Character) -> ToolResult:
        content = args.get("content", "")
        if not content:
            return ToolResult(success=False, message="没说什么")
        volume = args.get("volume", "normal")
        target = args.get("target", "")
        vol_label = {"whisper": "低声", "loud": "大声", "shout": "喊道"}.get(volume, "")
        broadcast = f"{caller.name}{vol_label}说：「{content}」"
        return ToolResult(
            message=f"你说: {content}",
            world_events=[{"content": broadcast, "event_type": "auditory"}],
        )

    def _exec_act(self, args: dict, caller: Character) -> ToolResult:
        description = args.get("description", "")
        if not description:
            return ToolResult(success=False, message="没有动作")

        duration = args.get("duration_seconds", 0.0)
        dx = args.get("move_dx", 0.0)
        dy = args.get("move_dy", 0.0)

        # 移动
        if dx != 0 or dy != 0:
            caller.position.move(dx, dy)

        # 记忆写入
        caller.memory.add_recent_event(f"做了: {description}", source="self")

        broadcast = f"{caller.name}{description}"
        events = [{"content": broadcast, "event_type": "visual"}]
        if dx != 0 or dy != 0:
            events.append({"content": f"{caller.name}移动了位置", "event_type": "visual"})

        return ToolResult(
            message=f"你做了: {description} ({duration:.0f}s)",
            world_events=events,
        )

    # ============================================================
    #  内部修改
    # ============================================================

    def _exec_set_goal(self, args: dict, caller: Character) -> ToolResult:
        goal = args.get("goal", "")
        if not goal:
            return ToolResult(success=False, message="目标不能为空")
        # 覆盖短期目标
        caller.memory.short_term.short_term_goals = [goal]
        return ToolResult(message=f"目标更新为: {goal}")

    def _exec_think(self, args: dict, caller: Character) -> ToolResult:
        content = args.get("content", "")
        emotion = args.get("emotion", "")
        if content:
            caller.memory.add_recent_event(f"想了: {content}", source="self")
        if emotion:
            caller.memory.add_recent_event(f"情绪: {emotion}", source="self")
        return ToolResult(message=f"内心: {content} [{emotion}]" if emotion else f"内心: {content}")

    def _exec_feel(self, args: dict, caller: Character) -> ToolResult:
        pain = float(args.get("pain", 0.0))
        fatigue = float(args.get("fatigue", 0.0))
        temperature = args.get("temperature", "normal")
        custom = args.get("custom", "")
        caller.body.apply_sensation(pain=pain, fatigue=fatigue, temperature=temperature)
        if custom:
            caller.memory.add_recent_event(f"感受: {custom}", source="self")
        return ToolResult(message=f"体感更新: pain={pain:.1f} fatigue={fatigue:.1f} temp={temperature}")

    # ============================================================
    #  物理效果
    # ============================================================

    def _get_target(self, target_name: str) -> Character | None:
        return self.character_map.get(target_name)

    def _exec_attack(self, args: dict, caller: Character) -> ToolResult:
        target_name = args.get("target", "")
        target = self._get_target(target_name)
        if not target:
            return ToolResult(success=False, message=f"找不到目标: {target_name}")
        body_part = args.get("body_part", "chest")
        damage = float(args.get("damage", 10))
        target.body.deal_damage(body_part, damage)
        broadcast = f"{caller.name}攻击了{target_name}的{body_part}"
        return ToolResult(
            message=f"你攻击了{target_name}的{body_part}，造成{damage}伤害",
            world_events=[{"content": broadcast, "event_type": "visual"}],
        )

    def _exec_bind(self, args: dict, caller: Character) -> ToolResult:
        target_name = args.get("target", "")
        target = self._get_target(target_name)
        if not target:
            return ToolResult(success=False, message=f"找不到目标: {target_name}")
        limb = args.get("limb", "right_hand")
        detail = args.get("detail", "被绳索绑住")
        target.body.bind_limb(limb, detail)
        broadcast = f"{caller.name}绑住了{target_name}的{limb}"
        return ToolResult(
            message=f"你绑住了{target_name}的{limb}",
            world_events=[{"content": broadcast, "event_type": "visual"}],
        )

    def _exec_unbind(self, args: dict, caller: Character) -> ToolResult:
        target_name = args.get("target", "")
        target = self._get_target(target_name)
        if not target:
            return ToolResult(success=False, message=f"找不到目标: {target_name}")
        limb = args.get("limb", "right_hand")
        target.body.unbind_limb(limb)
        broadcast = f"{caller.name}解开了{target_name}的{limb}"
        return ToolResult(
            message=f"你解开了{target_name}的{limb}",
            world_events=[{"content": broadcast, "event_type": "visual"}],
        )

    def _exec_heal(self, args: dict, caller: Character) -> ToolResult:
        target_name = args.get("target", "")
        target = self._get_target(target_name)
        if not target:
            return ToolResult(success=False, message=f"找不到目标: {target_name}")
        body_part = args.get("body_part", "chest")
        amount = float(args.get("amount", 10))
        target.body.heal(body_part, amount)
        broadcast = f"{caller.name}为{target_name}治疗了{body_part}"
        return ToolResult(
            message=f"你为{target_name}治疗了{body_part}，恢复{amount}",
            world_events=[{"content": broadcast, "event_type": "visual"}],
        )

    def _exec_push(self, args: dict, caller: Character) -> ToolResult:
        target_name = args.get("target", "")
        target = self._get_target(target_name)
        if not target:
            return ToolResult(success=False, message=f"找不到目标: {target_name}")
        direction = args.get("direction", "north")
        force = float(args.get("force", 1.0))
        dx, dy = {"north": (0, force), "south": (0, -force),
                   "east": (force, 0), "west": (-force, 0)}.get(direction, (0, 0))
        target.position.move(dx, dy)
        broadcast = f"{caller.name}把{target_name}往{direction}推"
        return ToolResult(
            message=f"你把{target_name}往{direction}推了{force}米",
            world_events=[{"content": broadcast, "event_type": "visual"}],
        )
