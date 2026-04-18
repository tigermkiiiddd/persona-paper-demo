"""
时间切片 - 叙事节奏的参数化控制

时间粒度可调：10秒/切片（慢描写）到 1天/切片（蒙太奇）。
粒度本身也是LLM能感知到的信息——"现在是慢镜头"vs"现在是一天过"。
"""

from pydantic import BaseModel, Field
from enum import Enum


class Tempo(str, Enum):
    """叙事节奏"""
    BULLET_TIME = "bullet_time"   # 子弹时间：3秒
    SLOW = "slow"                 # 慢描写：10秒
    NORMAL_SLOW = "normal_slow"   # 慢速：30秒
    NORMAL = "normal"             # 正常：1分钟
    NORMAL_FAST = "normal_fast"   # 快速：5分钟
    FAST = "fast"                 # 快叙事：15分钟
    FAST_HALF_HOUR = "fast_half_hour"  # 半小时级：30分钟
    FAST_HOUR = "fast_hour"       # 小时级：1小时
    FAST_TWO_HOUR = "fast_two_hour"  # 2小时级：2小时
    MONTAGE = "montage"           # 蒙太奇：6小时
    DAY = "day"                   # 日级：1天
    WEEK = "week"                 # 周级：1周


TEMPO_CONFIG = {
    Tempo.BULLET_TIME: {
        "seconds": 3,
        "llm_hint": "子弹时间，每个切片仅3秒。极度细致，描写每一瞬间：眼神变化、肌肉紧绷、气息、微动作。",
    },
    Tempo.SLOW: {
        "seconds": 10,
        "llm_hint": "慢描写，每个切片10秒。细致描写动作细节、微表情、内心波动。",
    },
    Tempo.NORMAL_SLOW: {
        "seconds": 30,
        "llm_hint": "慢速，每个切片30秒。关注对话节奏和动作的连贯性。",
    },
    Tempo.NORMAL: {
        "seconds": 60,
        "llm_hint": "正常节奏，每个切片约1分钟。按正常速度推进行为和对话。",
    },
    Tempo.NORMAL_FAST: {
        "seconds": 300,
        "llm_hint": "快速，每个切片5分钟。推进一段完整的对话或动作序列。",
    },
    Tempo.FAST: {
        "seconds": 900,
        "llm_hint": "快节奏，每个切片15分钟。概括关键行为，跳过琐碎细节。",
    },
    Tempo.FAST_HALF_HOUR: {
        "seconds": 1800,
        "llm_hint": "半小时级，每个切片30分钟。保留这段时间内的关键事件和对话，适度概括。",
    },
    Tempo.FAST_HOUR: {
        "seconds": 3600,
        "llm_hint": "小时级，每个切片1小时。只保留这段时间内的重要事件和对话。",
    },
    Tempo.FAST_TWO_HOUR: {
        "seconds": 7200,
        "llm_hint": "2小时级，每个切片2小时。高度概括，只描述这段时间内最重要的变化和转折。",
    },
    Tempo.MONTAGE: {
        "seconds": 21600,
        "llm_hint": "蒙太奇，每个切片6小时。高度概括，只描述最关键的转折。",
    },
    Tempo.DAY: {
        "seconds": 86400,
        "llm_hint": "日级，每个切片1天。概括一天中最重要的1-2件事。",
    },
    Tempo.WEEK: {
        "seconds": 604800,
        "llm_hint": "周级，每个切片1周。只描述这周内改变命运的事件。",
    },
}


class TimeSlice(BaseModel):
    """时间切片"""
    tempo: Tempo = Field(default=Tempo.NORMAL)
    slice_index: int = Field(default=0, ge=0, description="当前切片编号")
    elapsed_seconds: float = Field(default=0.0, description="从开始到现在经过的总秒数")

    @property
    def duration_seconds(self) -> float:
        return TEMPO_CONFIG[self.tempo]["seconds"]

    @property
    def llm_hint(self) -> str:
        return TEMPO_CONFIG[self.tempo]["llm_hint"]

    @property
    def slice_label(self) -> str:
        """人类可读的时间标签"""
        secs = self.elapsed_seconds
        if secs < 60:
            return f"{secs:.0f}秒"
        elif secs < 3600:
            return f"{secs/60:.0f}分"
        elif secs < 86400:
            return f"{secs/3600:.1f}小时"
        else:
            return f"{secs/86400:.1f}天"

    def advance(self) -> "TimeSlice":
        """推进到下一个切片"""
        return TimeSlice(
            tempo=self.tempo,
            slice_index=self.slice_index + 1,
            elapsed_seconds=self.elapsed_seconds + self.duration_seconds,
        )
