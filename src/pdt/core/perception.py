"""
感知器官 - 角色"硬件"层的物理约束过滤器

世界广播是全量的，但每个角色只能收到感知范围内的事。
眼睛=视锥+距离，耳朵=全向+距离衰减，身体=接触距离。
"""

import math
from pydantic import BaseModel, Field


class PerceptionResult(BaseModel):
    """感知过滤后的结果——角色实际能感知到的信息"""
    visual: list[str] = Field(default_factory=list, description="视觉：看到的事物")
    auditory: list[str] = Field(default_factory=list, description="听觉：听到的声音")
    tactile: list[str] = Field(default_factory=list, description="触觉：身体接触感受到的")

    @property
    def is_empty(self) -> bool:
        return not self.visual and not self.auditory and not self.tactile

    def summary(self) -> str:
        parts = []
        if self.visual:
            parts.append(f"看到{len(self.visual)}件事")
        if self.auditory:
            parts.append(f"听到{len(self.auditory)}件事")
        if self.tactile:
            parts.append(f"感受到{len(self.tactile)}件事")
        return "、".join(parts) if parts else "无感知"


class Eyes(BaseModel):
    """
    眼睛——视锥过滤，支持单眼/双眼/盲
    
    双眼正常: fov=150°, offset=0（对称视野）
    左眼瞎:   fov=120°, offset=+15°（视野中心偏右，左侧视野缩小）
    右眼瞎:   fov=120°, offset=-15°（视野中心偏左，右侧视野缩小）
    全瞎:     fov=0°（看不到任何视觉事件）
    """
    fov_degree: float = Field(default=150.0, description="总视野角度（度）")
    max_distance: float = Field(default=20.0, description="最大可视距离（米）")
    fov_offset: float = Field(
        default=0.0,
        description="视锥中心偏移（度）。正=右偏，负=左偏。左眼瞎→右偏，右眼瞎→左偏"
    )
    blind: bool = Field(default=False, description="是否全盲")

    def can_see(self, self_pos: tuple[float, float], self_facing: tuple[float, float],
                target_pos: tuple[float, float]) -> bool:
        if self.blind or self.fov_degree <= 0:
            return False
        dx = target_pos[0] - self_pos[0]
        dy = target_pos[1] - self_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > self.max_distance:
            return False
        if dist < 0.01:
            return True  # 同位置一定能看到
        angle = math.atan2(dy, dx)
        facing_angle = math.atan2(self_facing[1], self_facing[0])
        # 视锥中心偏移
        shifted_facing = facing_angle + math.radians(self.fov_offset)
        diff = abs(angle - shifted_facing)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        return diff <= math.radians(self.fov_degree / 2)

    @classmethod
    def normal(cls) -> "Eyes":
        """双眼正常"""
        return cls(fov_degree=150.0, fov_offset=0.0, blind=False)

    @classmethod
    def left_eye_blind(cls) -> "Eyes":
        """左眼瞎——视野中心偏右，总视野收窄"""
        return cls(fov_degree=120.0, fov_offset=15.0, blind=False)

    @classmethod
    def right_eye_blind(cls) -> "Eyes":
        """右眼瞎——视野中心偏左，总视野收窄"""
        return cls(fov_degree=120.0, fov_offset=-15.0, blind=False)

    @classmethod
    def fully_blind(cls) -> "Eyes":
        """全瞎"""
        return cls(fov_degree=0.0, blind=True)


class Ears(BaseModel):
    """耳朵——全向接收，距离衰减"""
    max_distance: float = Field(default=30.0, description="最大可听距离（米）")

    def can_hear(self, self_pos: tuple[float, float],
                 source_pos: tuple[float, float]) -> tuple[bool, float]:
        dx = source_pos[0] - self_pos[0]
        dy = source_pos[1] - self_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > self.max_distance:
            return False, 0.0
        attenuation = 1.0 - (dist / self.max_distance)
        return True, round(attenuation, 3)


class BodySense(BaseModel):
    """身体感知——接触距离"""
    contact_distance: float = Field(default=1.5, description="触觉感知距离（米）")

    def can_feel(self, self_pos: tuple[float, float],
                 target_pos: tuple[float, float]) -> bool:
        dx = target_pos[0] - self_pos[0]
        dy = target_pos[1] - self_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        return dist <= self.contact_distance


class PerceptionSystem(BaseModel):
    """完整的感知系统"""
    eyes: Eyes = Field(default_factory=Eyes)
    ears: Ears = Field(default_factory=Ears)
    body: BodySense = Field(default_factory=BodySense)

    def perceive(self, self_pos: tuple[float, float],
                 self_facing: tuple[float, float],
                 world_events: list["WorldEvent"]) -> PerceptionResult:
        """
        从世界全量事件中过滤出角色能感知到的子集。
        world_events 需要带 event_type(visual/auditory/tactile) 和 source_pos。
        """
        result = PerceptionResult()
        for evt in world_events:
            pos = evt.source_pos
            if evt.event_type == "visual":
                if self.eyes.can_see(self_pos, self_facing, pos):
                    result.visual.append(evt.content)
            elif evt.event_type == "auditory":
                can, volume = self.ears.can_hear(self_pos, pos)
                if can:
                    loudness = "隐约" if volume < 0.3 else ("清晰" if volume > 0.7 else "")
                    prefix = f"[{loudness}听到]" if loudness else "[听到]"
                    result.auditory.append(f"{prefix} {evt.content}")
            elif evt.event_type == "tactile":
                if self.body.can_feel(self_pos, pos):
                    result.tactile.append(evt.content)
        return result


# 延迟导入，避免循环引用
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .spatial import WorldEvent
