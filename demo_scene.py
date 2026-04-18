"""
Demo: 竹林茶馆 — 老儒生和女侠的生活场景

场景：江南小镇旁的竹林茶馆，一个隐居老儒生和一个路过的女侠在茶馆相遇。
10个切片的故事：从平静到危机到化险为夷。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.pdt.core.vector import CharacterVector, DimensionConfig, Dimension
from src.pdt.core.character import Character
from src.pdt.core.memory import MemoryLayer, LongTermMemory, ShortTermMemory
from src.pdt.core.spatial import Position, WorldEvent
from src.pdt.core.timeslice import Tempo
from src.pdt.engine.simulation import Simulation

# ============================================================
#  Helper: 快速创建 configs
# ============================================================

def make_configs(baselines=None, sensitivities=None, decay_rates=None):
    """快速生成 20 个 DimensionConfig"""
    defaults_b = [0.3, 0.5, 0.4, 0.3, 0.2, 0.5, 0.4, 0.3, 0.5, 0.6,
                  0.3, 0.0, 0.3, 0.0, 0.0, 0.3, 0.0, 0.0, 0.3, 0.0]
    defaults_s = [1.0] * 20
    defaults_d = [0.01, 0.01, 0.01, 0.01, 0.02, 0.01, 0.01, 0.02, 0.01, 0.01,
                  0.03, 0.05, 0.03, 0.04, 0.03, 0.02, 0.03, 0.04, 0.02, 0.04]
    b = baselines or defaults_b
    s = sensitivities or defaults_s
    d = decay_rates or defaults_d
    return [DimensionConfig(baseline=b[i], sensitivity=s[i], decay_rate=d[i]) for i in range(20)]


# ============================================================
#  创建角色
# ============================================================

# 老儒生 — 隐居茶馆的读书人
scholar = Character(
    name="老儒生",
    vector=CharacterVector(
        values=[
            -0.2, 0.6, 0.7, 0.8, -0.1,  # DOM AFF IND PRA VOL
            0.7, 0.5, -0.3, 0.8, 0.7,    # CUR SE RIS EMP MOR
            0.6, 0.7, 0.8, 0.7, 0.0,     # VIT SAT SEC COM LIB
            0.5, 0.3, 0.4, 0.2, -0.5,    # DES SHA SEN ATT REL
        ],
        configs=make_configs(
            baselines=[-0.2, 0.6, 0.7, 0.8, -0.1,
                       0.7, 0.5, -0.3, 0.8, 0.7,
                       0.3, 0.0, 0.3, 0.0, 0.0,  # VITALITY恢复型 baseline=0.3, SECURITY恢复型=0.3
                       0.3, 0.0, 0.0, 0.3, 0.0],
            sensitivities=[1.0, 1.2, 1.0, 1.0, 0.5,  # 低情绪敏感
                           1.2, 1.0, 0.8, 1.5, 1.3,    # 高好奇+高同理+高道德
                           1.0, 1.0, 1.0, 1.0, 0.5,
                           1.2, 0.8, 1.0, 0.8, 0.3],   # 低释放冲动敏感
        ),
    ),
    memory=MemoryLayer(
        long_term=LongTermMemory(
            world_view="天下大事分久必合合久必分，世事如棋",
            values="仁义礼智信，读书人的底线",
            love_view="少年时有一段情，已随岁月淡去",
            culture="前朝遗民，饱读诗书，隐居于此",
            trauma=["亲眼目睹旧朝覆灭", "学生背叛师门投靠权贵"],
            skills=["诗词", "书法", "茶道", "观人术", "围棋"],
            long_term_goals=["等一个值得传授毕生所学的人"],
        ),
        short_term=ShortTermMemory(
            short_term_goals=["泡一壶好茶", "读完手中的庄子"],
        ),
    ),
    position=Position(x=8, y=7),
    interruption_threshold=0.7,
)

# 女侠 — 江湖行走的女剑客
swordswoman = Character(
    name="女侠",
    vector=CharacterVector(
        values=[
            0.5, 0.3, 0.8, 0.4, 0.3,    # 有主见 不冷不热 极独立 偏感性 有波动
            0.6, 0.6, 0.7, 0.4, 0.5,     # 好奇 自信 敢冒险 有同理 侠义
            0.8, 0.4, 0.3, 0.3, 0.1,     # 年轻力壮 有点饿 戒备(初始低) 风尘仆仆
            0.3, 0.2, 0.5, 0.5, 0.2,     # 不太渴望被理解 不太羞耻 会享受 内心渴望归属
        ],
        configs=make_configs(
            baselines=[0.5, 0.3, 0.8, 0.4, 0.3,
                       0.6, 0.6, 0.7, 0.4, 0.5,
                       0.3, 0.0, 0.3, 0.0, 0.0,  # SECURITY baseline=0.3 恢复型
                       0.3, 0.0, 0.0, 0.3, 0.0],
            sensitivities=[1.0, 0.8, 1.0, 1.0, 1.5,  # 高情绪波动敏感
                           1.0, 1.0, 1.2, 0.8, 1.0,
                           1.0, 1.5, 2.0, 1.0, 0.5,   # SECURITY高敏感(江湖人警觉)
                           0.8, 0.5, 1.0, 1.3, 0.8],   # ATTACHMENT稍高敏感
        ),
    ),
    memory=MemoryLayer(
        long_term=LongTermMemory(
            world_view="江湖险恶，弱肉强食，但总有义士",
            values="侠之大者，为国为民；恩必偿，仇必报",
            love_view="师父说过，情之一字最误人，但她不信",
            culture="自幼习武，师父遭难后独自闯荡江湖",
            trauma=["师父被仇家所害", "被信任的同伴出卖过"],
            skills=["剑术", "轻功", "追踪术", "毒术辨识", "野外生存"],
            long_term_goals=["为师父报仇", "找到当年出卖师父的人"],
        ),
        short_term=ShortTermMemory(
            short_term_goals=["找个地方休息", "打听仇人下落"],
        ),
    ),
    position=Position(x=10, y=13),  # 院落，刚到
    interruption_threshold=0.4,
)

print(f"角色: {scholar.name} @ ({scholar.position.x}, {scholar.position.y})")
print(f"角色: {swordswoman.name} @ ({swordswoman.position.x}, {swordswoman.position.y})")


# ============================================================
#  创建模拟 + 事件时间线
# ============================================================

sim = Simulation(
    characters=[scholar, swordswoman],
    tempo=Tempo.NORMAL,  # 每切片1分钟
)

timeline = {
    0: [
        WorldEvent(content="远处传来马蹄声，由远及近", valence="neutral", event_category="information", source_pos=(12, 15),
                   event_type="auditory", intensity=0.3),
    ],
    1: [
        WorldEvent(content="一个身着青衣的女子走进茶馆，腰间佩剑，风尘仆仆", valence="neutral", event_category="scene",
                   source_pos=(10, 11), event_type="visual", intensity=0.7),
    ],
    2: [
        WorldEvent(content="女侠环顾四周，目光锐利，落在老儒生身上停了一瞬", valence="neutral", event_category="interpersonal",
                   source_pos=(10, 11), event_type="visual", intensity=0.5),
        WorldEvent(content="茶炉上的水开了，咕嘟咕嘟冒着热气", valence="neutral", event_category="environment",
                   source_pos=(10, 8), event_type="auditory", intensity=0.2),
    ],
    3: [
        WorldEvent(content="女侠在靠窗的位置坐下，将剑搁在桌上，要了一壶茶", valence="neutral", event_category="scene",
                   source_pos=(12, 6), event_type="visual", intensity=0.5),
    ],
    4: [
        WorldEvent(content="老儒生放下手中的书，对女侠微微点头致意", valence="positive", event_category="interpersonal",
                   source_pos=(8, 7), event_type="visual", intensity=0.4),
        WorldEvent(content="外面突然起了风，竹叶沙沙作响", valence="neutral", event_category="environment",
                   source_pos=(2, 5), event_type="auditory", intensity=0.3),
    ],
    5: [
        WorldEvent(content="女侠端起茶杯，目光从杯沿上方扫过老儒生的书——是一本《庄子》", valence="neutral", event_category="interpersonal",
                   source_pos=(12, 6), event_type="visual", intensity=0.6),
    ],
    6: [
        WorldEvent(content="两个黑衣人出现在茶馆门口，目光阴鸷，四处扫视", valence="negative", event_category="scene",
                   source_pos=(10, 11), event_type="visual", intensity=0.8),
        WorldEvent(content="女侠的手不动声色地搭上了剑柄", valence="negative", event_category="interpersonal",
                   source_pos=(12, 6), event_type="visual", intensity=0.7),
    ],
    7: [
        WorldEvent(content="黑衣人走向女侠，低声说：「奉主人之命，请姑娘移步」", valence="negative", event_category="interpersonal",
                   source_pos=(11, 6), event_type="auditory", intensity=0.8),
        WorldEvent(content="老儒生注意到了黑衣人腰间的令牌，瞳孔微缩", valence="negative", event_category="information",
                   source_pos=(8, 7), event_type="visual", intensity=0.5),
    ],
    8: [
        WorldEvent(content="女侠冷声道：「告诉你们主人，这笔账我迟早会去算」", valence="negative", event_category="interpersonal",
                   source_pos=(12, 6), event_type="auditory", intensity=0.9),
        WorldEvent(content="黑衣人后退一步，手按刀柄，气氛骤然紧张", valence="negative", event_category="interpersonal",
                   source_pos=(10, 11), event_type="visual", intensity=0.8),
    ],
    9: [
        WorldEvent(content="老儒生缓缓起身，走到黑衣人面前，淡淡说：「年轻人，在别人的茶馆里动刀兵，不合适吧？」", valence="neutral", event_category="interpersonal",
                   source_pos=(9, 8), event_type="auditory", intensity=0.6),
        WorldEvent(content="黑衣人看到老儒生的眼神，犹豫了一瞬", valence="neutral", event_category="interpersonal",
                   source_pos=(10, 11), event_type="visual", intensity=0.5),
    ],
}

sim.set_scene_timeline(timeline)

# ============================================================
#  运行模拟
# ============================================================

print("\n" + "=" * 70)
print("  竹林茶馆 — 模拟开始")
print("=" * 70)

SHOW_DIMS = {
    "SECURITY": "安全感",
    "VOLATILITY": "情绪",
    "COMFORT": "舒适",
    "RELEASE_IMPULSE": "释放冲动",
    "ATTACHMENT": "依恋",
    "EMPATHY": "同理心",
}

for i in range(10):
    snapshot = sim.step()
    idx = snapshot.slice_index
    elapsed = snapshot.elapsed_label

    print(f"\n{'─' * 70}")
    print(f"  切片 {idx}  ({elapsed})")
    print(f"{'─' * 70}")

    for char in sim.characters:
        data = snapshot.characters.get(char.name, {})
        drives = data.get("drive_breakdown", {})
        force = data.get("drive_force", 0)
        perception = data.get("perception", {})
        pos = data.get("position", {})
        body = data.get("body", {})

        print(f"\n  【{char.name}】 @ ({pos.get('x','?')}, {pos.get('y','?')})")
        print(f"    HP: {body.get('hp','?'):.2f}  心率: {body.get('heart_rate','?')}  驱动力: {force:.3f}")

        # 感知
        vis = perception.get("visual", [])
        aud = perception.get("auditory", [])
        tac = perception.get("tactile", [])
        if vis:
            for v in vis[:2]:
                print(f"    👁 {v[:65]}{'...' if len(v) > 65 else ''}")
        if aud:
            for a in aud[:2]:
                print(f"    👂 {a[:65]}{'...' if len(a) > 65 else ''}")
        if tac:
            for t in tac:
                print(f"    ✋ {t[:65]}")

        # 核心维度
        dim_strs = []
        for dim_name, cn in SHOW_DIMS.items():
            dim = Dimension[dim_name]
            v = char.vector.get_value(dim)
            bar_len = int(abs(v) * 10)
            if v >= 0:
                bar = "█" * bar_len + "░" * (10 - bar_len)
            else:
                bar = "░" * (10 - bar_len) + "█" * bar_len
            dim_strs.append(f"{cn}={v:+.2f}")
        print(f"    {' | '.join(dim_strs)}")

        # 驱动力
        drive_strs = []
        for cat, val in sorted(drives.items()):
            if abs(val) > 0.05:
                drive_strs.append(f"{cat}={val:+.2f}")
        if drive_strs:
            print(f"    驱动: {', '.join(drive_strs[:6])}")

print(f"\n{'=' * 70}")
print("  模拟结束")
print(f"{'=' * 70}")
