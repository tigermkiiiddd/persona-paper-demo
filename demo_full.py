"""
完整实战验证：时间切片同步模拟

每回合 = 一个时间切片（~1分钟）
所有角色同时接收所有广播信息，同时输出
完整历史记录每轮都传给LLM
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and value and key not in os.environ:
                os.environ[key] = value

from pdt.core.vector import CharacterVector, Dimension, DIMENSION_NAMES
from pdt.core.memory import MemoryLayer, LongTermMemory, ShortTermMemory
from pdt.core.event import Event, EventType, Valence, Duration
from pdt.core.causal import CausalEngine
from pdt.core.character import Character
from pdt.llm.behavior import BehaviorGenerator


def create_old_scholar() -> Character:
    values = [
        -0.3, 0.4, 0.8, 0.6, -0.6, 0.1, 0.2, -0.5,
        0.5, 0.7, -0.2, 0.3, 0.6, 0.5, -0.8, 0.6,
        0.3, 0.1, -0.4, -0.6,
    ]
    sensitivities = [
        0.5, 0.6, 0.8, 0.7, 0.3, 0.2, 0.5, 0.6,
        0.5, 0.7, 0.8, 0.3, 0.7, 0.5, 0.1, 0.6,
        0.4, 0.2, 0.3, 0.2,
    ]
    decay_rates = [
        0.02, 0.03, 0.02, 0.03, 0.04, 0.02, 0.02, 0.03,
        0.02, 0.01, 0.08, 0.12, 0.08, 0.10, 0.05, 0.04,
        0.06, 0.05, 0.03, 0.04,
    ]
    vector = CharacterVector.create(values, values.copy(), sensitivities, decay_rates)
    causal = CausalEngine.create_from_overrides(default_weight=0.5)
    memory = MemoryLayer(
        long_term=LongTermMemory(
            world_view="儒家入世思想但已失望，认为世人愚昧",
            values="仁义礼智信，但不强求他人",
            love_view="夫妻应当相敬如宾，但聚散随缘",
            culture="书香门第，读书人做派，说话带文言气",
            trauma=["年轻时官场被排挤，被迫隐居"],
            skills=["经史子集", "天文地理", "书法"],
            long_term_goals=["写完一部传世之作"],
        ),
        short_term=ShortTermMemory(short_term_goals=["写书"]),
    )
    return Character(name="老儒生", vector=vector, memory=memory,
                     causal_engine=causal, interruption_threshold=0.7)


def create_swordswoman() -> Character:
    values = [
        0.5, -0.2, 0.9, 0.7, 0.3, 0.6, 0.6, 0.8,
        0.2, 0.3, 0.7, 0.3, 0.5, 0.4, 0.2, 0.1,
        -0.3, 0.4, -0.2, 0.5,
    ]
    sensitivities = [
        0.7, 0.5, 0.8, 0.7, 0.6, 0.6, 0.7, 0.5,
        0.3, 0.4, 0.6, 0.5, 0.7, 0.5, 0.3, 0.2,
        0.3, 0.5, 0.3, 0.7,
    ]
    decay_rates = [
        0.03, 0.04, 0.02, 0.03, 0.05, 0.03, 0.02, 0.03,
        0.03, 0.02, 0.08, 0.10, 0.08, 0.10, 0.06, 0.04,
        0.06, 0.06, 0.04, 0.05,
    ]
    vector = CharacterVector.create(values, values.copy(), sensitivities, decay_rates)
    causal = CausalEngine.create_from_overrides(default_weight=0.5)
    memory = MemoryLayer(
        long_term=LongTermMemory(
            world_view="江湖道义，弱肉强食",
            values="欠债还钱，恩怨分明",
            love_view="感情是累赘",
            culture="江湖出身，说话直爽粗犷",
            trauma=["被师父背叛"],
            skills=["剑术", "轻功", "江湖情报"],
            long_term_goals=["找到背叛师父的人报仇"],
        ),
        short_term=ShortTermMemory(short_term_goals=["逃跑", "处理伤口"]),
    )
    return Character(name="女侠", vector=vector, memory=memory,
                     causal_engine=causal, interruption_threshold=0.4)


SLICE_SECONDS = 60

SCENE_TIMELINE = {
    0: Event(event_type=EventType.INTERPERSONAL, intensity=0.7,
             source="陌生女子", content="一个浑身血迹的女人踹开门冲进来，手持长剑，衣衫满是血迹",
             valence=Valence.NEGATIVE, duration=Duration.INSTANT_PLUS_SUSTAINED),
    2: Event(event_type=EventType.ENVIRONMENT, intensity=0.5,
             source="远方", content="隐隐约约听到远处有马蹄声",
             valence=Valence.NEGATIVE, duration=Duration.SUSTAINED),
    3: Event(event_type=EventType.ENVIRONMENT, intensity=0.7,
             source="追兵", content="马蹄声越来越近，有人在喊叫",
             valence=Valence.NEGATIVE, duration=Duration.SUSTAINED),
    4: Event(event_type=EventType.INTERPERSONAL, intensity=0.85,
             source="追兵", content="追兵到达！为首的人下马冲着茅屋喊：'那个女人在里面吧？识相的把她交出来！'",
             valence=Valence.NEGATIVE, duration=Duration.INSTANT),
    5: Event(event_type=EventType.INTERPERSONAL, intensity=0.9,
             source="追兵首领", content="追兵首领踢开门拔刀指着屋内：'老东西，最后警告一次，交人！否则连你一起砍了！'",
             valence=Valence.NEGATIVE, duration=Duration.INSTANT),
}

CHASER_THREAT_BASE = 0.3
CHASER_THREAT_START = 2
CHASER_THREAT_INCREMENT = 0.05


def snapshot(vector: CharacterVector) -> dict[str, float]:
    return {DIMENSION_NAMES[Dimension(i)][1]: round(vector.values[i], 3) for i in range(20)}


def infer_valence(text: str) -> Valence:
    neg = ["攻击","怒","骂","杀","打","滚","拒绝","威胁","哼","恨","叛","砍","拔刀","冲"]
    pos = ["帮","谢","好","笑","友","关心","保护","多谢","请"]
    for kw in neg:
        if kw in text:
            return Valence.NEGATIVE
    for kw in pos:
        if kw in text:
            return Valence.POSITIVE
    return Valence.NEUTRAL


def infer_intensity(text: str) -> float:
    for kw in ["拔刀","冲","砍","杀","踢","砸"]:
        if kw in text:
            return 0.7
    return 0.4


SYSTEM_PROMPT_TEMPLATE = """你是「人格演绎剧场」的行为生成引擎。
你的任务是扮演指定角色，根据角色的内在状态（20维向量）和完整历史记录，生成该角色在当前时间切片内（约1分钟）的行为。

## 角色身份
{identity}

## 严格输出格式

你必须且只能输出以下JSON格式，不要添加任何其他字段：
{{
  "speech": "角色说的话，沉默则为空字符串",
  "action": "角色的身体动作描述",
  "internal_thought": "角色内心的想法",
  "emotion": "当前主要情绪",
  "target_goal": "当前想做的事",
  "interrupting": false
}}"""


def build_identity(character: Character) -> str:
    parts = [f"角色名字：{character.name}。"]
    lt = character.memory.long_term
    if lt.culture:
        parts.append(f"文化背景：{lt.culture}。")
    if lt.trauma:
        parts.append(f"创伤经历：{'；'.join(lt.trauma)}。")
    if lt.long_term_goals:
        parts.append(f"人生追求：{'；'.join(lt.long_term_goals)}。")
    if character.memory.short_term.short_term_goals:
        parts.append(f"当前在做的事：{'；'.join(character.memory.short_term.short_term_goals)}。")
    return "\n".join(parts)


def generate_slice_action(
    client, model: str, system_prompt: str,
    character: Character, slice_num: int,
    current_broadcast: str, history_text: str,
) -> dict:
    elapsed_min = slice_num * SLICE_SECONDS / 60
    
    can_int, force, _ = character.should_interrupt()
    
    user_content = f"""## 角色内在状态（20维向量）
{character.get_state_summary()}

## 时间切片 #{slice_num}（{elapsed_min:.0f}分钟时）

## 完整历史记录（从最开始到现在）
{history_text}

## 本切片新增的广播信息
{current_broadcast}

## 驱动力状态
当前驱动力: {force:.2f}, 打断阈值: {character.interruption_threshold}
{'驱动力超过阈值，角色可能在此时做出强烈反应。' if can_int else ''}

请参考你的历史行为，做出接下来约1分钟内的行为推理。严格按JSON格式输出。"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
        timeout=60,
    )
    
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {
            "speech": resp.choices[0].message.content,
            "action": "", "internal_thought": "",
            "emotion": "未知", "target_goal": "未知", "interrupting": False,
        }


def run():
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("PDT_MODEL", "gpt-4")
    
    if not api_key:
        print("错误: 请配置 .env")
        sys.exit(1)
    
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    scholar = create_old_scholar()
    swordswoman = create_swordswoman()
    
    # 构建各自的system prompt
    sys_prompt_a = SYSTEM_PROMPT_TEMPLATE.format(identity=build_identity(scholar))
    sys_prompt_b = SYSTEM_PROMPT_TEMPLATE.format(identity=build_identity(swordswoman))
    
    baseline_a = snapshot(scholar.vector)
    baseline_b = snapshot(swordswoman.vector)
    
    # 完整历史记录
    history: list[str] = []
    
    print("=" * 70)
    print("  人格演绎剧场 - 时间切片同步模拟")
    print("=" * 70)
    print(f"  模型: {model}")
    print(f"  时间切片: {SLICE_SECONDS}秒/切片")
    print(f"  模式: 广播同步，完整历史记录")
    print(f"  角色: 老儒生(隐居写书) + 女侠(受伤逃亡)")
    print()
    
    total_slices = 7
    
    for slice_num in range(total_slices):
        elapsed = slice_num * SLICE_SECONDS
        elapsed_min = elapsed / 60
        
        print(f"{'═' * 70}")
        print(f"  时间切片 #{slice_num} | {elapsed_min:.0f}分{elapsed % 60:.0f}秒")
        print(f"{'═' * 70}")
        
        # ---- 1. 收集本切片的场景广播 ----
        current_broadcasts: list[str] = []
        
        scene_event = SCENE_TIMELINE.get(slice_num)
        if scene_event:
            current_broadcasts.append(f"[场景] {scene_event.content}")
            scholar.process_event(scene_event)
            swordswoman.process_event(scene_event)
        
        if slice_num >= CHASER_THREAT_START:
            threat = CHASER_THREAT_BASE + (slice_num - CHASER_THREAT_START) * CHASER_THREAT_INCREMENT
            threat_event = Event(
                event_type=EventType.ENVIRONMENT,
                intensity=min(threat, 0.95),
                source="追兵逼近",
                content=f"追兵压力持续增加，马蹄声更近了",
                valence=Valence.NEGATIVE, duration=Duration.SUSTAINED,
            )
            current_broadcasts.append(f"[持续] 追兵逼近，威胁等级{threat:.1f}")
            scholar.process_event(threat_event)
            swordswoman.process_event(threat_event)
        
        current_broadcast = "\n".join(current_broadcasts) if current_broadcasts else "没有新的场景事件。"
        history_text = "\n".join(history) if history else "（无历史记录，这是第一个切片）"
        
        print(f"\n  【本切片广播】")
        for b in current_broadcasts:
            print(f"    {b}")
        
        # ---- 2. 两个角色同时生成行为 ----
        
        # 老儒生
        print(f"\n  [老儒生 生成中...]")
        before_a = snapshot(scholar.vector)
        action_a = generate_slice_action(client, model, sys_prompt_a, scholar, slice_num, current_broadcast, history_text)
        speech_a = action_a.get("speech", "")
        act_a = action_a.get("action", "")
        thought_a = action_a.get("internal_thought", "")
        emotion_a = action_a.get("emotion", "")
        goal_a = action_a.get("target_goal", "")
        after_a = snapshot(scholar.vector)
        can_int_a, force_a, _ = scholar.should_interrupt()
        
        print(f"    语言: {speech_a}")
        if act_a: print(f"    动作: {act_a}")
        if thought_a: print(f"    内心: {thought_a}")
        if emotion_a: print(f"    情绪: {emotion_a}")
        if goal_a: print(f"    目标: {goal_a}")
        print(f"    驱动力: {force_a:.2f}")
        for key in before_a:
            delta = after_a[key] - before_a[key]
            if abs(delta) > 0.005:
                print(f"    {key}: {before_a[key]:+.3f} -> {after_a[key]:+.3f}")
        
        # 女侠
        print(f"\n  [女侠 生成中...]")
        before_b = snapshot(swordswoman.vector)
        action_b = generate_slice_action(client, model, sys_prompt_b, swordswoman, slice_num, current_broadcast, history_text)
        speech_b = action_b.get("speech", "")
        act_b = action_b.get("action", "")
        thought_b = action_b.get("internal_thought", "")
        emotion_b = action_b.get("emotion", "")
        goal_b = action_b.get("target_goal", "")
        after_b = snapshot(swordswoman.vector)
        can_int_b, force_b, _ = swordswoman.should_interrupt()
        
        print(f"    语言: {speech_b}")
        if act_b: print(f"    动作: {act_b}")
        if thought_b: print(f"    内心: {thought_b}")
        if emotion_b: print(f"    情绪: {emotion_b}")
        if goal_b: print(f"    目标: {goal_b}")
        print(f"    驱动力: {force_b:.2f}")
        for key in before_b:
            delta = after_b[key] - before_b[key]
            if abs(delta) > 0.005:
                print(f"    {key}: {before_b[key]:+.3f} -> {after_b[key]:+.3f}")
        
        # ---- 3. 互相作为事件输入 + 记忆写回 ----
        if speech_a or act_a:
            bcast_a = f"老儒生{act_a}。" + (f"老儒生说：「{speech_a}」" if speech_a else "")
            event_a = Event(
                event_type=EventType.INTERPERSONAL, intensity=infer_intensity(bcast_a),
                source="老儒生", content=bcast_a,
                valence=infer_valence(bcast_a), duration=Duration.INSTANT,
            )
            swordswoman.process_event(event_a)
            scholar.memory.add_recent_event(bcast_a)
        
        if speech_b or act_b:
            bcast_b = f"女侠{act_b}。" + (f"女侠说：「{speech_b}」" if speech_b else "")
            event_b = Event(
                event_type=EventType.INTERPERSONAL, intensity=infer_intensity(bcast_b),
                source="女侠", content=bcast_b,
                valence=infer_valence(bcast_b), duration=Duration.INSTANT,
            )
            scholar.process_event(event_b)
            swordswoman.memory.add_recent_event(bcast_b)
        
        # ---- 4. 记入历史 ----
        if scene_event:
            history.append(f"[{elapsed_min:.0f}分] 场景: {scene_event.content}")
        if slice_num >= CHASER_THREAT_START:
            threat = CHASER_THREAT_BASE + (slice_num - CHASER_THREAT_START) * CHASER_THREAT_INCREMENT
            history.append(f"[{elapsed_min:.0f}分] 追兵逼近，威胁等级{threat:.1f}")
        if speech_a or act_a:
            history.append(f"[{elapsed_min:.0f}分] 老儒生: {act_a}" + (f" 说：「{speech_a}」" if speech_a else ""))
        if speech_b or act_b:
            history.append(f"[{elapsed_min:.0f}分] 女侠: {act_b}" + (f" 说：「{speech_b}」" if speech_b else ""))
        
        # ---- 5. 时间推进 ----
        scholar.tick()
        swordswoman.tick()
        
        print()
    
    # ====== 稳态验证 ======
    print(f"{'═' * 70}")
    print(f"  稳态验证: 交互结束后维度是否回归基线（100 tick后）")
    print(f"{'═' * 70}")
    
    for _ in range(100):
        scholar.tick()
        swordswoman.tick()
    
    final_a = snapshot(scholar.vector)
    final_b = snapshot(swordswoman.vector)
    
    print(f"\n  [老儒生]")
    a_ok, a_total = 0, 0
    for key in baseline_a:
        if abs(baseline_a[key]) > 0.05:
            a_total += 1
            dev = abs(final_a[key] - baseline_a[key])
            ok = dev < 0.1
            a_ok += ok
            print(f"    {key:<25} 基线{baseline_a[key]:>+7.3f} -> 最终{final_a[key]:>+7.3f} 偏差{dev:.3f} {'✓' if ok else '✗'}")
    
    print(f"\n  [女侠]")
    b_ok, b_total = 0, 0
    for key in baseline_b:
        if abs(baseline_b[key]) > 0.05:
            b_total += 1
            dev = abs(final_b[key] - baseline_b[key])
            ok = dev < 0.1
            b_ok += ok
            print(f"    {key:<25} 基线{baseline_b[key]:>+7.3f} -> 最终{final_b[key]:>+7.3f} 偏差{dev:.3f} {'✓' if ok else '✗'}")
    
    print(f"\n  老儒生回归: {a_ok}/{a_total}")
    print(f"  女侠回归: {b_ok}/{b_total}")
    print(f"  事件稳态: {'通过 ✓' if a_ok == a_total and b_ok == b_total else '未完全通过 ✗'}")


if __name__ == "__main__":
    run()
