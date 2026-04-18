"""
身体状态 - 角色的持续内在信息源

三层维护：
1. 代码维护：生命体征、感官状态、肢体部位（数值驱动）
2. LLM输出驱动：体感描述（pain/fatigue/temperature），代码写入下一轮注入
3. Tool calling：动作触发物理效果（A绑B的手 → B的limb状态改变）
"""

from pydantic import BaseModel, Field
from enum import Enum


class LimbStatus(str, Enum):
    """肢体状态"""
    NORMAL = "normal"
    INJURED = "injured"       # 受伤
    BOUND = "bound"           # 被绑
    CRIPPLED = "crippled"     # 残缺/残废
    SEVERED = "severed"       # 断裂


class Limb(BaseModel):
    """单个肢体/部位"""
    name: str = Field(description="部位名")
    status: LimbStatus = Field(default=LimbStatus.NORMAL)
    hp: float = Field(default=100.0, ge=0.0, le=100.0, description="部位生命值")
    detail: str = Field(default="", description="额外描述")


class HeartRate(str, Enum):
    CALM = "calm"
    ELEVATED = "elevated"
    RACING = "racing"


def _default_limbs() -> dict[str, Limb]:
    return {
        "head": Limb(name="头"),
        "chest": Limb(name="胸"),
        "back": Limb(name="背"),
        "left_arm": Limb(name="左臂"),
        "right_arm": Limb(name="右臂"),
        "left_hand": Limb(name="左手"),
        "right_hand": Limb(name="右手"),
        "left_leg": Limb(name="左腿"),
        "right_leg": Limb(name="右腿"),
    }


class BodyState(BaseModel):
    """角色的完整身体状态——持续信息源"""

    # 生命体征（代码维护）
    hp: float = Field(default=100.0, ge=0.0, le=100.0, description="总体生命值")
    heart_rate: HeartRate = Field(default=HeartRate.CALM, description="心率")

    # 各肢体部位（代码维护 + tool calling 修改）
    limbs: dict[str, Limb] = Field(default_factory=_default_limbs)

    # 体感（LLM输出驱动）
    pain: float = Field(default=0.0, ge=0.0, le=1.0, description="疼痛 0-1")
    fatigue: float = Field(default=0.0, ge=0.0, le=1.0, description="疲劳 0-1")
    temperature_feel: str = Field(default="normal", description="温度感: cold/cool/normal/warm/hot")

    # ============================================================
    #  查询接口
    # ============================================================

    def get_impaired_limbs(self) -> list[Limb]:
        """返回所有非正常状态的肢体"""
        return [l for l in self.limbs.values() if l.status != LimbStatus.NORMAL]

    def can_use(self, limb_name: str) -> bool:
        """某肢体是否可用"""
        limb = self.limbs.get(limb_name)
        if not limb:
            return False
        return limb.status in (LimbStatus.NORMAL, LimbStatus.INJURED) and limb.hp > 0

    def is_alive(self) -> bool:
        return self.hp > 0

    # ============================================================
    #  格式化输出（注入prompt）
    # ============================================================

    def to_prompt_text(self) -> str:
        """格式化为LLM能理解的身体状态文本"""
        parts = []
        parts.append(f"生命值: {self.hp:.0f}/100")
        parts.append(f"心率: {self.heart_rate.value}")

        impaired = self.get_impaired_limbs()
        if impaired:
            parts.append("异常部位:")
            for limb in impaired:
                label = f"{limb.name}: {limb.status.value}"
                if limb.detail:
                    label += f" ({limb.detail})"
                parts.append(f"  {label}")

        if self.pain > 0.1:
            level = "轻微" if self.pain < 0.4 else ("明显" if self.pain < 0.7 else "剧烈")
            parts.append(f"疼痛: {level}({self.pain:.0%})")
        if self.fatigue > 0.1:
            level = "轻微" if self.fatigue < 0.4 else ("明显" if self.fatigue < 0.7 else "极度")
            parts.append(f"疲劳: {level}({self.fatigue:.0%})")
        if self.temperature_feel != "normal":
            parts.append(f"温度感: {self.temperature_feel}")

        return "\n".join(parts)

    # ============================================================
    #  Tool calling 接口（动作触发物理效果）
    # ============================================================

    def deal_damage(self, limb_name: str, amount: float) -> None:
        """对某部位造成伤害"""
        if limb_name not in self.limbs:
            return
        limb = self.limbs[limb_name]
        limb.hp = max(0.0, limb.hp - amount)
        if limb.hp < 30:
            limb.status = LimbStatus.INJURED
        # 总hp = 各部位均值
        self.hp = sum(l.hp for l in self.limbs.values()) / len(self.limbs)
        # 心率反应
        if amount > 20:
            self.heart_rate = HeartRate.RACING
        elif amount > 5:
            if self.heart_rate == HeartRate.CALM:
                self.heart_rate = HeartRate.ELEVATED

    def heal(self, limb_name: str, amount: float) -> None:
        """治疗某部位"""
        if limb_name not in self.limbs:
            return
        limb = self.limbs[limb_name]
        limb.hp = min(100.0, limb.hp + amount)
        if limb.hp >= 50 and limb.status == LimbStatus.INJURED:
            limb.status = LimbStatus.NORMAL
        self.hp = sum(l.hp for l in self.limbs.values()) / len(self.limbs)

    def bind_limb(self, limb_name: str, detail: str = "被绳索绑住") -> None:
        """绑住某部位"""
        if limb_name in self.limbs:
            self.limbs[limb_name].status = LimbStatus.BOUND
            self.limbs[limb_name].detail = detail

    def unbind_limb(self, limb_name: str) -> None:
        """解开某部位"""
        if limb_name in self.limbs and self.limbs[limb_name].status == LimbStatus.BOUND:
            self.limbs[limb_name].status = LimbStatus.NORMAL
            self.limbs[limb_name].detail = ""

    def cripple_limb(self, limb_name: str) -> None:
        """致残某部位"""
        if limb_name in self.limbs:
            self.limbs[limb_name].status = LimbStatus.CRIPPLED
            self.limbs[limb_name].hp = 0

    # ============================================================
    #  LLM输出驱动接口
    # ============================================================

    def apply_sensation(self, pain: float = 0.0, fatigue: float = 0.0,
                        temperature: str = "normal") -> None:
        """应用LLM输出的体感（增量更新）"""
        self.pain = min(1.0, max(0.0, self.pain + pain))
        self.fatigue = min(1.0, max(0.0, self.fatigue + fatigue))
        if temperature != "normal":
            self.temperature_feel = temperature

    # ============================================================
    #  时间推进
    # ============================================================

    def tick(self, dt: float = 1.0) -> None:
        """时间推进：体感自然衰减，心率恢复"""
        decay = dt * 0.01
        self.pain = max(0.0, self.pain - decay)
        self.fatigue = max(0.0, self.fatigue - decay * 0.5)
        # 心率逐步恢复
        if self.heart_rate == HeartRate.RACING:
            self.heart_rate = HeartRate.ELEVATED
        elif self.heart_rate == HeartRate.ELEVATED:
            self.heart_rate = HeartRate.CALM
