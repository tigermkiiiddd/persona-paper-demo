"""
因果关系图引擎

维度之间的因果方向固定，影响权重个性化。
规则通用，数值驱动，涌现人格。
"""

from pydantic import BaseModel, Field
from .vector import Dimension, CharacterVector


class CausalEdge(BaseModel):
    """一条因果边（模板，定义默认方向）"""
    source: Dimension = Field(description="源维度")
    target: Dimension = Field(description="目标维度")
    default_direction: int = Field(ge=-1, le=1, description="默认方向: 1=同向, -1=反向")
    description: str = Field(description="因果关系说明")


class PersonalizedEdge(BaseModel):
    """个性化的因果边：方向和权重都可以因人而异"""
    edge_index: int = Field(description="对应CAUSAL_GRAPH中的边索引")
    direction: int = Field(ge=-1, le=1, description="个性化方向: 1=同向, -1=反向。大多数人遵循默认，少数人反转（如危险→兴奋）")
    weight: float = Field(ge=0.0, le=2.0, description="个性化影响权重")


# 固定的因果关系图 - 22条边
CAUSAL_GRAPH: list[CausalEdge] = [
    # 生理驱动 → 生理驱动
    CausalEdge(source=Dimension.SATIATION, target=Dimension.COMFORT, default_direction=1,
               description="饥饿→舒适度：饿了就不舒服（默认同向：满足高→舒适高）"),
    CausalEdge(source=Dimension.VITALITY, target=Dimension.COMFORT, default_direction=1,
               description="生命力→舒适度：身体差就不舒服"),
    CausalEdge(source=Dimension.COMFORT, target=Dimension.VOLATILITY, default_direction=-1,
               description="舒适度→情绪波动：不舒服就易怒（默认反向）"),
    CausalEdge(source=Dimension.SECURITY, target=Dimension.COMFORT, default_direction=1,
               description="安全感→舒适度：不安全就不舒服"),
    CausalEdge(source=Dimension.LIBIDO, target=Dimension.RELEASE_IMPULSE, default_direction=1,
               description="性冲动→释放冲动：性冲动强更容易过激"),
    CausalEdge(source=Dimension.SENSORY_PLEASURE, target=Dimension.COMFORT, default_direction=1,
               description="感官愉悦→舒适度：愉悦提升舒适"),
    # 生理驱动 → 性格/欲望
    CausalEdge(source=Dimension.SATIATION, target=Dimension.RISK_TOLERANCE, default_direction=-1,
               description="饥饿→风险承受：饿急了铤而走险（满足低→风险承受反而高，所以默认反向）"),
    CausalEdge(source=Dimension.SECURITY, target=Dimension.CURIOSITY, default_direction=1,
               description="安全感→好奇心：害怕就不探索（默认同向）。反转者：危险反而兴奋想探索"),
    CausalEdge(source=Dimension.VITALITY, target=Dimension.CURIOSITY, default_direction=1,
               description="生命力→好奇心：没精力就不探索"),
    CausalEdge(source=Dimension.SECURITY, target=Dimension.DOMINANCE, default_direction=-1,
               description="安全感→掌控欲：不安全就想要控制（默认反向）。反转者：越安全越想掌控"),
    CausalEdge(source=Dimension.SHAME, target=Dimension.RELEASE_IMPULSE, default_direction=1,
               description="羞耻感→释放冲动：羞耻驱动过激行为。反转者：羞耻反而更压抑"),
    # 性格 → 生理/欲望
    CausalEdge(source=Dimension.CURIOSITY, target=Dimension.RISK_TOLERANCE, default_direction=1,
               description="好奇心→风险承受：好奇就敢冒险"),
    CausalEdge(source=Dimension.EMPATHY, target=Dimension.AFFECTION, default_direction=1,
               description="同理心→亲和度：共情驱动友好"),
    CausalEdge(source=Dimension.MORAL_ALIGNMENT, target=Dimension.RELEASE_IMPULSE, default_direction=-1,
               description="道德准则→释放冲动：有原则更克制（默认反向）"),
    CausalEdge(source=Dimension.SELF_ESTEEM, target=Dimension.SHAME, default_direction=-1,
               description="自尊心→羞耻感：自信的人不易羞耻（默认反向）"),
    CausalEdge(source=Dimension.DOMINANCE, target=Dimension.INDEPENDENCE, default_direction=1,
               description="掌控欲→独立性：想控制就要自主"),
    # 性格 → 性格
    CausalEdge(source=Dimension.PRAGMATISM, target=Dimension.VOLATILITY, default_direction=-1,
               description="务实性→情绪波动：理性的人情绪更稳（默认反向）"),
    CausalEdge(source=Dimension.SELF_ESTEEM, target=Dimension.ATTACHMENT, default_direction=-1,
               description="自尊心→依恋需求：自卑更需要依附（默认反向）"),
    CausalEdge(source=Dimension.EMPATHY, target=Dimension.DESIRE_UNDERSTANDING, default_direction=1,
               description="同理心→渴望被理解：能共情就更想被理解"),
    # 欲望 → 性格
    CausalEdge(source=Dimension.ATTACHMENT, target=Dimension.AFFECTION, default_direction=1,
               description="依恋需求→亲和度：依恋驱动友好"),
    CausalEdge(source=Dimension.DESIRE_UNDERSTANDING, target=Dimension.CURIOSITY, default_direction=1,
               description="渴望被理解→好奇心：想被理解就去探索他人"),
    CausalEdge(source=Dimension.RELEASE_IMPULSE, target=Dimension.VOLATILITY, default_direction=1,
               description="释放冲动→情绪波动：压抑不住就更波动"),
]


class CausalEngine(BaseModel):
    """因果关系图引擎 - 每个角色拥有一套个性化的因果边"""
    
    # 每条边的个性化配置，key = edge index
    edges: dict[int, PersonalizedEdge] = Field(
        default_factory=dict,
        description="个性化因果边：方向和权重都是角色的固有属性"
    )
    
    # 因果传播的衰减系数，防止震荡
    propagation_factor: float = Field(
        default=0.3,
        ge=0.0, le=1.0,
        description="因果传播系数，控制因果影响的强度"
    )
    
    def _get_direction(self, edge_index: int) -> int:
        """获取某条边的个性化方向，未配置则用默认"""
        if edge_index in self.edges:
            return self.edges[edge_index].direction
        return CAUSAL_GRAPH[edge_index].default_direction
    
    def _get_weight(self, edge_index: int) -> float:
        """获取某条边的个性化权重"""
        if edge_index in self.edges:
            return self.edges[edge_index].weight
        return 0.5  # 默认权重
    
    def propagate(self, vector: CharacterVector, changed_dims: set[Dimension]) -> dict[Dimension, float]:
        """
        因果传播：已改变的维度通过因果图影响其他维度。
        每个角色的因果方向和权重不同，所以同一个事件对不同角色产生不同影响。
        """
        deltas: dict[int, float] = {}
        
        for i, edge in enumerate(CAUSAL_GRAPH):
            if edge.source not in changed_dims:
                continue
            
            direction = self._get_direction(i)
            weight = self._get_weight(i)
            source_deviation = vector.get_deviation(edge.source)
            
            # 因果影响 = 源维度偏差 × 个性化方向 × 个性化权重 × 传播系数
            delta = source_deviation * direction * weight * self.propagation_factor
            target_idx = edge.target.value
            deltas[target_idx] = deltas.get(target_idx, 0.0) + delta
        
        # 应用因果偏移
        result: dict[Dimension, float] = {}
        new_changed: set[Dimension] = set()
        for dim_idx, delta in deltas.items():
            if abs(delta) < 0.001:
                continue
            dim = Dimension(dim_idx)
            old_val = vector.get_value(dim)
            new_val = max(-1.0, min(1.0, old_val + delta))
            actual = new_val - old_val
            if abs(actual) > 0.001:
                vector.set_value(dim, new_val)
                result[dim] = actual
                new_changed.add(dim)
        
        # 递归传播一层（最多两层，防止无限循环）
        if new_changed:
            for i, edge in enumerate(CAUSAL_GRAPH):
                if edge.source not in new_changed:
                    continue
                if edge.target in changed_dims or edge.target in new_changed:
                    continue  # 避免回路
                
                direction = self._get_direction(i)
                weight = self._get_weight(i)
                source_deviation = vector.get_deviation(edge.source)
                delta = source_deviation * direction * weight * self.propagation_factor * 0.5
                target_idx = edge.target.value
                
                dim = Dimension(target_idx)
                old_val = vector.get_value(dim)
                new_val = max(-1.0, min(1.0, old_val + delta))
                actual = new_val - old_val
                if abs(actual) > 0.001:
                    vector.set_value(dim, new_val)
                    result[dim] = actual
        
        return result
    
    @classmethod
    def create(cls, edges: dict[int, PersonalizedEdge] | None = None) -> "CausalEngine":
        """便捷构造"""
        return cls(edges=edges or {}, propagation_factor=0.3)
    
    @classmethod
    def create_from_overrides(
        cls,
        direction_overrides: dict[int, int] | None = None,
        weight_overrides: dict[int, float] | None = None,
        default_weight: float = 0.5,
    ) -> "CausalEngine":
        """
        便捷构造：只指定需要覆盖的边，其余用默认值。
        direction_overrides: {edge_index: direction} 方向反转的边
        weight_overrides: {edge_index: weight} 权重不同的边
        """
        edges: dict[int, PersonalizedEdge] = {}
        
        # 所有22条边都生成配置
        for i in range(len(CAUSAL_GRAPH)):
            direction = CAUSAL_GRAPH[i].default_direction
            weight = default_weight
            
            if direction_overrides and i in direction_overrides:
                direction = direction_overrides[i]
            if weight_overrides and i in weight_overrides:
                weight = weight_overrides[i]
            
            edges[i] = PersonalizedEdge(
                edge_index=i,
                direction=direction,
                weight=weight,
            )
        
        return cls(edges=edges, propagation_factor=0.3)
