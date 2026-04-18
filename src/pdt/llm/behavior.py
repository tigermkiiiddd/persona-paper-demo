"""
LLM行为生成层 v3 — Tool Calling + 工具链

LLM不再输出JSON行为，而是通过 function calling 调用工具。
一次LLM调用可以连续调用多个工具（工具链）。
"""

import json
from openai import OpenAI
from ..core.character import Character, DriveCategory, DRIVE_CATEGORY_NAMES
from ..core.perception import PerceptionResult
from ..core.timeslice import TimeSlice
from ..core.spatial import WorldEvent
from ..core.vector import Dimension, DIMENSION_NAMES, DIMENSION_DESCRIPTIONS
from ..engine.tools import tools_to_openai_format, all_tool_names
from ..engine.executor import ToolExecutor, ToolResult


SYSTEM_PROMPT = """你是「人格推演沙盘」的行为生成引擎。

你的任务是根据角色的内在状态、记忆、身体状态和当前感知信息，通过调用工具来执行行为。

## 核心规则

1. 20个维度是角色的驱动层。你根据维度值推断角色会怎么做。
2. 情绪是维度的涌现结果。
3. 角色只能看到感知范围内的信息。
4. 身体状态会限制行为（手被绑就不能用手，受伤就不能剧烈运动）。
5. 你通过调用工具来行动。可以一次调用多个工具（工具链）。
6. 参考你的历史行为，避免重复。

## 工具分类

- **外部行为** (speak, act): 产生世界事件，其他人能看到/听到
- **内部修改** (set_goal, think, feel): 只改自己的内部状态，其他人看不到
- **物理效果** (attack, bind, unbind, heal, push): 修改他人的物理状态

## 维度解释

{dimension_details}
"""

OUTPUT_HINT = """
## 工具调用策略

- 你可以一次调用多个工具，按顺序执行。
- 典型的工具链：先 think() 思考，再 set_goal() 决定目标，然后 speak()/act() 执行外部行为，最后 feel() 记录体感。
- 内部工具（think/set_goal/feel）不会暴露给其他人。
- 你不是每次都要调用所有工具。安静的时候可能只需要 think()。
- 不说话就不调用 speak()，不动就不调用 act()。
"""


def build_dimension_details() -> str:
    lines = []
    for dim in Dimension:
        desc = DIMENSION_DESCRIPTIONS[dim]
        cn_name, en_name = DIMENSION_NAMES[dim]
        lines.append(f"### {cn_name} ({en_name})")
        lines.append(f"  范围 [-1.0, +1.0]")
        lines.append(f"  min(-1.0): {desc['neg']}")
        lines.append(f"  max(+1.0): {desc['pos']}")
        lines.append(f"  注: {desc['note']}")
        lines.append("")
    return "\n".join(lines)


class BehaviorGenerator:
    """LLM行为生成器 v3 — Tool Calling"""

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.system_prompt = SYSTEM_PROMPT.format(
            dimension_details=build_dimension_details()
        )
        self.openai_tools = tools_to_openai_format()

    def build_user_prompt(
        self,
        character: Character,
        time_slice: TimeSlice,
        perception: PerceptionResult,
    ) -> str:
        parts = []

        # 角色状态
        parts.append(f"## 角色状态\n{character.get_state_summary()}")

        # 时间
        parts.append(f"\n## 时间信息\n"
                      f"当前切片: #{time_slice.slice_index}，已过 {time_slice.slice_label}\n"
                      f"切片时长: {time_slice.duration_seconds:.0f}秒\n"
                      f"{time_slice.llm_hint}")

        # 感知
        parts.append(f"\n## 当前感知\n{character.format_perception_for_prompt(perception)}")

        # 驱动力
        can_int, force, drives = character.should_interrupt()
        parts.append(f"\n## 驱动力状态\n"
                      f"总驱动力: {force:.2f}, 打断阈值: {character.interruption_threshold:.2f}")
        # 分类明细
        drive_lines = []
        for cat in DriveCategory:
            cn = DRIVE_CATEGORY_NAMES[cat]
            val = drives.get(cat, 0)
            drive_lines.append(f"  {cn}: {val:.3f}")
        parts.append("\n".join(drive_lines))
        if can_int:
            parts.append("驱动力超过阈值，角色可能在此时做出强烈反应。")

        parts.append(f"\n{OUTPUT_HINT}")

        return "\n".join(parts)

    def generate(
        self,
        character: Character,
        time_slice: TimeSlice,
        perception: PerceptionResult,
        executor: ToolExecutor,
        max_chains: int = 5,
    ) -> list[ToolResult]:
        """
        生成角色在当前切片的行为。支持工具链。
        
        返回所有工具调用的结果列表。
        """
        user_prompt = self.build_user_prompt(character, time_slice, perception)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        all_results: list[ToolResult] = []

        for chain_idx in range(max_chains):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.openai_tools,
                tool_choice="auto",
                temperature=0.8,
                timeout=60,
            )

            msg = response.choices[0].message

            # 没有工具调用 → 结束
            if not msg.tool_calls:
                break

            # 记录 assistant 的工具调用
            messages.append(msg.model_dump())

            # 执行每个工具调用
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                result = executor.execute(fn_name, fn_args, character)

                # 记录工具结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result.message,
                })

                all_results.append(result)

            # 如果 stop_reason 是 stop，不再继续
            if response.choices[0].finish_reason == "stop":
                break

        return all_results
