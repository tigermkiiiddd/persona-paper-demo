"""
空间模型 - 角色的世界坐标、朝向、世界事件的空间属性
"""

import math
from pydantic import BaseModel, Field


class Position(BaseModel):
    """2D世界坐标 + 朝向"""
    x: float = Field(default=0.0, description="X坐标（米）")
    y: float = Field(default=0.0, description="Y坐标（米）")
    facing_x: float = Field(default=0.0, description="朝向向量X分量")
    facing_y: float = Field(default=1.0, description="朝向向量Y分量")

    def pos_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def facing_tuple(self) -> tuple[float, float]:
        return (self.facing_x, self.facing_y)

    def move(self, dx: float, dy: float) -> None:
        """移动，同时更新朝向为移动方向"""
        if abs(dx) > 0.001 or abs(dy) > 0.001:
            length = math.sqrt(dx * dx + dy * dy)
            self.facing_x = dx / length
            self.facing_y = dy / length
        self.x += dx
        self.y += dy

    def face(self, fx: float, fy: float) -> None:
        """设置朝向"""
        length = math.sqrt(fx * fx + fy * fy)
        if length > 0:
            self.facing_x = fx / length
            self.facing_y = fy / length

    def distance_to(self, other: "Position") -> float:
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx * dx + dy * dy)

    def __repr__(self) -> str:
        return f"Pos({self.x:.1f}, {self.y:.1f}) facing({self.facing_x:.2f}, {self.facing_y:.2f})"


class WorldEvent(BaseModel):
    """世界中的事件（带空间位置），用于感知过滤"""
    content: str = Field(description="事件描述")
    source_pos: tuple[float, float] = Field(default=(0.0, 0.0), description="事件源位置")
    event_type: str = Field(default="visual", description="感知通道: visual/auditory/tactile")
    intensity: float = Field(default=1.0, ge=0.0, le=1.0, description="原始强度")
    valence: str = Field(default="neutral", description="效价: positive/negative/neutral")
    event_category: str = Field(default="environment", description="事件类别: interpersonal/environment/body/information/scene")
