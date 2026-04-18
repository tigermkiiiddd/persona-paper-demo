"""
场景系统 — 2D tile-based 世界地图

场景由网格组成，每格一个 tile。场景上可放置物体和标记区域。
角色的 Position(x, y) 直接对应 tile 坐标。
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


# ============================================================
#  地形类型
# ============================================================

class Terrain(str, Enum):
    """地形类型"""
    EMPTY = "empty"         # 空地/室内地板
    GRASS = "grass"         # 草地
    DIRT = "dirt"           # 泥地
    STONE = "stone"         # 石板路
    WATER = "water"         # 水（不可通行）
    DEEP_WATER = "deep_water"  # 深水
    SAND = "sand"           # 沙地
    SNOW = "snow"           # 雪
    WALL = "wall"           # 墙壁（不可通行）
    FOREST = "forest"       # 森林（减速）
    SWAMP = "swamp"         # 沼泽（减速）
    LAVA = "lava"           # 岩浆（伤害）
    WOOD = "wood"           # 木地板
    CARPET = "carpet"       # 地毯


# ============================================================
#  物体类型
# ============================================================

class ObjectType(str, Enum):
    """场景物体类型"""
    TREE = "tree"               # 树
    ROCK = "rock"               # 岩石
    BUSH = "bush"               # 灌木
    CAMPFIRE = "campfire"       # 篝火
    CHEST = "chest"             # 宝箱
    DOOR = "door"               # 门
    FENCE = "fence"             # 栅栏
    TABLE = "table"             # 桌子
    CHAIR = "chair"             # 椅子
    BED = "bed"                 # 床
    SIGNPOST = "signpost"       # 路标
    WELL = "well"               # 水井
    HOUSE = "house"             # 房屋
    BRIDGE = "bridge"           # 桥
    CUSTOM = "custom"           # 自定义物体


# ============================================================
#  区域类型
# ============================================================

class ZoneType(str, Enum):
    """区域标记"""
    SAFE = "safe"               # 安全区
    DANGER = "danger"           # 危险区
    REST = "rest"               # 休息区
    SOCIAL = "social"           # 社交区
    SPAWN = "spawn"             # 出生点
    EXIT = "exit"               # 出口
    QUEST = "quest"             # 任务区
    CUSTOM = "custom"           # 自定义


# ============================================================
#  通行性
# ============================================================

BLOCKED_TERRAINS = {Terrain.WALL, Terrain.WATER, Terrain.DEEP_WATER, Terrain.LAVA}
SLOW_TERRAINS = {Terrain.FOREST, Terrain.SWAMP}

BLOCKED_OBJECTS = {ObjectType.ROCK, ObjectType.HOUSE, ObjectType.WELL, ObjectType.FENCE}

# ============================================================
#  地形/物体 属性表
# ============================================================

TERRAIN_PROPS: dict[Terrain, dict] = {
    Terrain.EMPTY:       {"passable": True,  "speed_mult": 1.0, "color": "#1a1a2e", "label": "空地"},
    Terrain.GRASS:       {"passable": True,  "speed_mult": 1.0, "color": "#2d5016", "label": "草地"},
    Terrain.DIRT:        {"passable": True,  "speed_mult": 1.0, "color": "#5c4033", "label": "泥地"},
    Terrain.STONE:       {"passable": True,  "speed_mult": 1.0, "color": "#6b6b6b", "label": "石板"},
    Terrain.WATER:       {"passable": False, "speed_mult": 0.0, "color": "#1a4a6b", "label": "水"},
    Terrain.DEEP_WATER:  {"passable": False, "speed_mult": 0.0, "color": "#0d2f4f", "label": "深水"},
    Terrain.SAND:        {"passable": True,  "speed_mult": 0.8, "color": "#c2a645", "label": "沙地"},
    Terrain.SNOW:        {"passable": True,  "speed_mult": 0.7, "color": "#d4d4d4", "label": "雪"},
    Terrain.WALL:        {"passable": False, "speed_mult": 0.0, "color": "#3a3a3a", "label": "墙壁"},
    Terrain.FOREST:      {"passable": True,  "speed_mult": 0.5, "color": "#1a3a0a", "label": "森林"},
    Terrain.SWAMP:       {"passable": True,  "speed_mult": 0.4, "color": "#2a3a1a", "label": "沼泽"},
    Terrain.LAVA:        {"passable": False, "speed_mult": 0.0, "color": "#8b1a1a", "label": "岩浆"},
    Terrain.WOOD:        {"passable": True,  "speed_mult": 1.0, "color": "#6b4226", "label": "木地板"},
    Terrain.CARPET:      {"passable": True,  "speed_mult": 1.0, "color": "#4a1a3a", "label": "地毯"},
}

OBJECT_PROPS: dict[ObjectType, dict] = {
    ObjectType.TREE:     {"passable": False, "color": "#0a5c0a", "label": "树", "symbol": "🌲"},
    ObjectType.ROCK:     {"passable": False, "color": "#555555", "label": "岩石", "symbol": "🪨"},
    ObjectType.BUSH:     {"passable": True,  "color": "#2a6a1a", "label": "灌木", "symbol": "🌿"},
    ObjectType.CAMPFIRE: {"passable": False, "color": "#ff6600", "label": "篝火", "symbol": "🔥"},
    ObjectType.CHEST:    {"passable": True,  "color": "#8b6914", "label": "宝箱", "symbol": "📦"},
    ObjectType.DOOR:     {"passable": True,  "color": "#6b3a1a", "label": "门", "symbol": "🚪"},
    ObjectType.FENCE:    {"passable": False, "color": "#4a3a2a", "label": "栅栏", "symbol": "▯"},
    ObjectType.TABLE:    {"passable": False, "color": "#6b4226", "label": "桌子", "symbol": "▭"},
    ObjectType.CHAIR:    {"passable": True,  "color": "#5a3a1a", "label": "椅子", "symbol": "≐"},
    ObjectType.BED:      {"passable": False, "color": "#3a2a5a", "label": "床", "symbol": "▭"},
    ObjectType.SIGNPOST: {"passable": True,  "color": "#6b5a3a", "label": "路标", "symbol": "⚞"},
    ObjectType.WELL:     {"passable": False, "color": "#4a4a5a", "label": "水井", "symbol": "⊙"},
    ObjectType.HOUSE:    {"passable": False, "color": "#5a3a2a", "label": "房屋", "symbol": "⌂"},
    ObjectType.BRIDGE:   {"passable": True,  "color": "#7a5a3a", "label": "桥", "symbol": "="},
    ObjectType.CUSTOM:   {"passable": True,  "color": "#888888", "label": "自定义", "symbol": "?"},
}


# ============================================================
#  数据模型
# ============================================================

class Tile(BaseModel):
    """单个网格"""
    terrain: Terrain = Field(default=Terrain.EMPTY)
    # 可选的地形旋转/变体
    variant: int = Field(default=0, ge=0, le=3, description="地形变体编号(0-3)")


class SceneObject(BaseModel):
    """场景中的物体"""
    id: str = Field(description="唯一ID")
    type: ObjectType = Field(default=ObjectType.CUSTOM)
    x: int = Field(ge=0, description="X坐标(tile)")
    y: int = Field(ge=0, description="Y坐标(tile)")
    name: str = Field(default="", description="物体名称")
    description: str = Field(default="", description="物体描述")
    passable: Optional[bool] = Field(default=None, description="覆盖默认通行性")
    # 自定义属性（如宝箱内容、门的开关状态等）
    properties: dict = Field(default_factory=dict)


class Zone(BaseModel):
    """区域标记（矩形范围）"""
    id: str = Field(description="唯一ID")
    type: ZoneType = Field(default=ZoneType.CUSTOM)
    name: str = Field(default="")
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    description: str = Field(default="")
    properties: dict = Field(default_factory=dict)


class SpawnPoint(BaseModel):
    """角色出生点"""
    character_name: str = Field(description="角色名")
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    facing_x: float = Field(default=0.0)
    facing_y: float = Field(default=1.0)


class Scene(BaseModel):
    """完整场景"""
    id: str = Field(description="场景唯一ID")
    name: str = Field(default="未命名场景")
    description: str = Field(default="")
    width: int = Field(default=32, ge=4, le=256, description="场景宽度(tiles)")
    height: int = Field(default=32, ge=4, le=256, description="场景高度(tiles)")
    tile_size: float = Field(default=1.0, description="每格对应的世界米数")

    # 地形层：二维数组，height 行 x width 列
    tiles: list[list[Tile]] = Field(default_factory=list)

    # 物体层
    objects: list[SceneObject] = Field(default_factory=list)

    # 区域层
    zones: list[Zone] = Field(default_factory=list)

    # 角色出生点
    spawn_points: list[SpawnPoint] = Field(default_factory=list)

    # 世界环境变量（默认值）
    default_weather: str = Field(default="clear")
    default_temperature: float = Field(default=20.0)
    default_time_of_day: str = Field(default="morning")

    def init_tiles(self) -> None:
        """初始化空地形"""
        if not self.tiles:
            self.tiles = [
                [Tile() for _ in range(self.width)]
                for _ in range(self.height)
            ]

    def get_tile(self, x: int, y: int) -> Tile | None:
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.tiles[y][x]
        return None

    def set_tile(self, x: int, y: int, terrain: Terrain) -> None:
        if 0 <= y < self.height and 0 <= x < self.width:
            self.tiles[y][x] = Tile(terrain=terrain)

    def is_passable(self, x: int, y: int) -> bool:
        """检查某个 tile 是否可通行（地形+物体）"""
        tile = self.get_tile(x, y)
        if tile is None:
            return False
        terrain_ok = TERRAIN_PROPS.get(tile.terrain, {}).get("passable", True)
        # 检查该位置是否有阻挡物体
        for obj in self.objects:
            if obj.x == x and obj.y == y:
                obj_pass = obj.passable if obj.passable is not None else OBJECT_PROPS.get(obj.type, {}).get("passable", True)
                if not obj_pass:
                    return False
        return terrain_ok

    def get_objects_at(self, x: int, y: int) -> list[SceneObject]:
        return [o for o in self.objects if o.x == x and o.y == y]

    def get_zones_at(self, x: int, y: int) -> list[Zone]:
        result = []
        for z in self.zones:
            if z.x <= x < z.x + z.width and z.y <= y < z.y + z.height:
                result.append(z)
        return result
