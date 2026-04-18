"""
demo_v3 — 用 Simulation 引擎跑同样的场景
"""

import sys, os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and value and key not in os.environ:
                os.environ[key] = value

from pdt.core.vector import CharacterVector
from pdt.core.memory import MemoryLayer, LongTermMemory, ShortTermMemory
from pdt.core.causal import CausalEngine
from pdt.core.character import Character
from pdt.core.spatial import WorldEvent
from pdt.core.timeslice import Tempo

from pdt.engine.simulation import Simulation
from pdt.llm.behavior import BehaviorGenerator


def create_old_scholar() -> Character:
    values = [-0.3, 0.4, 0.8, 0.6, -0.6, 0.1, 0.2, -0.5,
              0.5, 0.7, -0.2, 0.7, 0.6, 0.5, -0.8, 0.6, 0.3, 0.3, -0.4, -0.6]
    vector = CharacterVector.create(initial_values=values, sensitivities=[0.5]*20, decay_rates=[0.03]*20)
    memory = MemoryLayer(
        long_term=LongTermMemory(
            world_view="儒家入世思想但已失望",
            values="仁义礼智信，但不强求他人",
            culture="书香门第，说话带文言气",
            trauma=["年轻时官场被排挤，被迫隐居"],
            skills=["经史子集", "天文地理", "书法"],
            long_term_goals=["写完一部传世之作"],
        ),
        short_term=ShortTermMemory(short_term_goals=["写书"]),
    )
    return Character(
        name="老儒生", vector=vector, memory=memory,
        causal_engine=CausalEngine.create_from_overrides(default_weight=0.5),
        interruption_threshold=0.7,
    )


def create_swordswoman() -> Character:
    values = [0.5, -0.2, 0.9, 0.7, 0.3, 0.6, 0.6, 0.8,
              0.2, 0.3, 0.7, 0.6, 0.5, 0.4, 0.2, 0.1, -0.3, 0.4, -0.2, 0.5]
    vector = CharacterVector.create(initial_values=values, sensitivities=[0.5]*20, decay_rates=[0.03]*20)
    memory = MemoryLayer(
        long_term=LongTermMemory(
            world_view="江湖道义，弱肉强食",
            values="欠债还钱，恩怨分明",
            culture="江湖出身，说话直爽粗犷",
            trauma=["被师父背叛"],
            skills=["剑术", "轻功", "江湖情报"],
            long_term_goals=["找到背叛师父的人报仇"],
        ),
        short_term=ShortTermMemory(short_term_goals=["逃跑", "处理伤口"]),
    )
    sw = Character(
        name="女侠", vector=vector, memory=memory,
        causal_engine=CausalEngine.create_from_overrides(default_weight=0.5),
        interruption_threshold=0.4,
    )
    sw.body.deal_damage("left_arm", 30)
    sw.body.apply_sensation(pain=0.5, fatigue=0.3)
    return sw


SCENE_TIMELINE = {
    0: [
        WorldEvent(content="一个浑身血迹的女人踹开门冲进来，手持长剑", source_pos=(5.0, 0.0), event_type="visual", intensity=0.8),
        WorldEvent(content="门板碎裂的巨响", source_pos=(5.0, 0.0), event_type="auditory", intensity=0.9),
    ],
    2: [
        WorldEvent(content="隐隐约约听到远处有马蹄声", source_pos=(30.0, 30.0), event_type="auditory", intensity=0.4),
    ],
    3: [
        WorldEvent(content="马蹄声越来越近，有人在喊叫", source_pos=(15.0, 15.0), event_type="auditory", intensity=0.6),
    ],
    4: [
        WorldEvent(content="追兵到达！为首的人下马冲着茅屋喊", source_pos=(8.0, 0.0), event_type="auditory", intensity=0.8),
        WorldEvent(content="追兵在门外", source_pos=(8.0, 0.0), event_type="visual", intensity=0.7),
    ],
    5: [
        WorldEvent(content="追兵首领踢开门拔刀指着屋内", source_pos=(6.0, 0.0), event_type="visual", intensity=0.9),
        WorldEvent(content="'老东西，最后警告一次，交人！否则连你一起砍了！'", source_pos=(6.0, 0.0), event_type="auditory", intensity=0.9),
    ],
}


def print_snapshot(snapshot):
    """打印切片结果"""
    print(f"\n{'═' * 60}")
    print(f"  切片 #{snapshot.slice_index} | {snapshot.elapsed_label}")
    print(f"{'═' * 60}")

    for char_name, data in snapshot.characters.items():
        print(f"\n  [{char_name}]")

        # 感知
        p = data["perception"]
        pcount = len(p["visual"]) + len(p["auditory"]) + len(p["tactile"])
        if pcount > 0:
            parts = []
            if p["visual"]: parts.append(f"看到{len(p['visual'])}件")
            if p["auditory"]: parts.append(f"听到{len(p['auditory'])}件")
            if p["tactile"]: parts.append(f"感受{len(p['tactile'])}件")
            print(f"    感知: {'、'.join(parts)}")

        # 工具调用结果
        for tr in data.get("tool_results", []):
            if tr["success"]:
                print(f"    >> {tr['message']}")

        # 身体
        body = data.get("body", {})
        if body.get("impaired"):
            print(f"    受伤部位: {', '.join(body['impaired'])}")

        print(f"    驱动力: {data['drive_force']:.2f}")


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("PDT_MODEL", "gpt-4")

    if not api_key:
        print("错误: 请配置 .env")
        sys.exit(1)

    gen = BehaviorGenerator(api_key=api_key, base_url=base_url, model=model)

    scholar = create_old_scholar()
    swordswoman = create_swordswoman()

    sim = Simulation(
        characters=[scholar, swordswoman],
        tempo=Tempo.FAST_HALF_HOUR,
        behavior_generator=gen,
    )
    sim.set_scene_timeline(SCENE_TIMELINE)

    print("=" * 60)
    print("  人格推演沙盘 — Simulation Engine v3")
    print("=" * 60)
    print(f"  模型: {model}")
    print(f"  节奏: fast_half_hour (30分钟/切片)")
    print(f"  角色: 老儒生 + 女侠(左臂受伤)")
    print(f"  自触发规则: {len(sim.self_triggers)}条")

    sim.run(num_slices=10, callback=print_snapshot)

    # 稳态验证
    print(f"\n{'═' * 60}")
    print(f"  稳态验证（100 tick后）")
    print(f"{'═' * 60}")
    for _ in range(100):
        for char in sim.characters:
            char.tick()
    for char in sim.characters:
        print(f"\n  [{char.name}]")
        print(f"    HP: {char.body.hp:.0f}/100")
        impaired = char.body.get_impaired_limbs()
        if impaired:
            for l in impaired:
                print(f"    {l.name}: {l.status.value} ({l.hp:.0f})")

    print("\n  完成.")


if __name__ == "__main__":
    main()
