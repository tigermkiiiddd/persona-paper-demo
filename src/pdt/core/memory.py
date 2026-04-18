"""
记忆层 - 角色的所有后天积累

本我是出厂设置，记忆是人生经历。
失忆了行为会变，但底色不变。

记忆条目结构化，按 source 分组（自己 vs 外界），缓存友好。
"""

from pydantic import BaseModel, Field


class LongTermMemory(BaseModel):
    """长期记忆（稳定，几乎不变）"""
    world_view: str = Field(default="", description="世界观：怎么看待这个世界")
    values: str = Field(default="", description="价值观：什么重要什么不重要")
    love_view: str = Field(default="", description="爱情观：怎么看待爱情和亲密关系")
    culture: str = Field(default="", description="文化背景：在什么环境长大，影响语言风格和行为习惯")
    trauma: list[str] = Field(default_factory=list, description="创伤/执念：过往经历中留下深刻印记的事件")
    skills: list[str] = Field(default_factory=list, description="知识/技能：学过的东西，累积型")
    long_term_goals: list[str] = Field(default_factory=list, description="长期目标/人生追求")


class Relationship(BaseModel):
    """对某个其他角色的关系映射"""
    target_name: str = Field(description="对方的名字或标识")
    impression: str = Field(default="", description="整体印象")
    trust: float = Field(default=0.0, ge=-1.0, le=1.0, description="信任度")
    emotional_valence: float = Field(default=0.0, ge=-1.0, le=1.0, description="情感倾向 -1厌恶 +1喜爱")
    interaction_count: int = Field(default=0, description="交互次数")
    key_events: list[str] = Field(default_factory=list, description="关键交互事件")


class MemoryEntry(BaseModel):
    """单条结构化记忆"""
    timestamp: float = Field(default=0.0, description="世界时间（秒）")
    category: str = Field(default="event", description="分类: event/action/speech/emotion/perception")
    content: str = Field(default="", description="内容")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要度")
    source: str = Field(default="environment", description="来源: self/environment/other")


class ShortTermMemory(BaseModel):
    """短期记忆（动态，随时变化）"""
    relationships: dict[str, Relationship] = Field(
        default_factory=dict,
        description="人际关系映射，key=对方名字"
    )
    entries: list[MemoryEntry] = Field(
        default_factory=list,
        description="结构化记忆条目"
    )
    short_term_goals: list[str] = Field(
        default_factory=list,
        description="短期目标/当前任务"
    )

    @property
    def recent_events(self) -> list[str]:
        """兼容旧接口"""
        return [f"[{e.category}] {e.content}" for e in self.entries]

    def add_entry(self, category: str, content: str, timestamp: float = 0.0,
                  importance: float = 0.5, source: str = "environment") -> None:
        """添加结构化记忆条目"""
        self.entries.append(MemoryEntry(
            timestamp=timestamp, category=category,
            content=content, importance=importance, source=source,
        ))
        # 超过上限时按重要度淘汰最旧的
        if len(self.entries) > 30:
            self.entries.sort(key=lambda e: e.importance, reverse=True)
            self.entries = self.entries[:25]
            self.entries.sort(key=lambda e: e.timestamp)


class MemoryLayer(BaseModel):
    """完整的记忆层"""
    long_term: LongTermMemory = Field(default_factory=LongTermMemory)
    short_term: ShortTermMemory = Field(default_factory=ShortTermMemory)

    def add_recent_event(self, event: str, source: str = "environment",
                         category: str = "event", importance: float = 0.5,
                         timestamp: float = 0.0) -> None:
        """添加近期事件（兼容旧接口 + 支持结构化参数）"""
        self.short_term.add_entry(
            category=category, content=event,
            timestamp=timestamp, importance=importance, source=source,
        )

    def update_relationship(self, name: str, **kwargs) -> Relationship:
        """更新或创建关系"""
        if name not in self.short_term.relationships:
            self.short_term.relationships[name] = Relationship(target_name=name)
        rel = self.short_term.relationships[name]
        for key, value in kwargs.items():
            if hasattr(rel, key):
                setattr(rel, key, value)
        rel.interaction_count += 1
        return rel

    def consolidate_event(self, event: str, memory_type: str = "trauma") -> None:
        """短期记忆沉淀为长期记忆"""
        if memory_type == "trauma":
            self.long_term.trauma.append(event)
        elif memory_type == "skill":
            self.long_term.skills.append(event)

    def get_context_for_prompt(self) -> str:
        """生成给LLM的记忆上下文，按 source 分组"""
        parts = []

        # 长期记忆（稳定，不变）
        lt = self.long_term
        if lt.world_view or lt.values or lt.love_view:
            parts.append("【三观】")
            if lt.world_view:
                parts.append(f"  世界观: {lt.world_view}")
            if lt.values:
                parts.append(f"  价值观: {lt.values}")
            if lt.love_view:
                parts.append(f"  爱情观: {lt.love_view}")

        if lt.culture:
            parts.append(f"【文化背景】{lt.culture}")

        if lt.trauma:
            parts.append(f"【创伤/执念】{'；'.join(lt.trauma)}")

        if lt.skills:
            parts.append(f"【知识/技能】{', '.join(lt.skills)}")

        if lt.long_term_goals:
            parts.append(f"【长期目标】{'；'.join(lt.long_term_goals)}")

        # 短期记忆按 source 分组
        self_actions = [e for e in self.short_term.entries if e.source == "self"]
        other_events = [e for e in self.short_term.entries if e.source != "self"]

        if self_actions:
            parts.append("【你的历史行为】")
            for e in self_actions[-8:]:
                parts.append(f"  - {e.content}")

        if other_events:
            parts.append("【外界事件】")
            for e in other_events[-5:]:
                parts.append(f"  - {e.content}")

        # 人际关系
        if self.short_term.relationships:
            parts.append("【人际关系】")
            for name, rel in self.short_term.relationships.items():
                trust_str = f"信任{rel.trust:+.1f}" if rel.trust != 0 else ""
                emo_str = f"情感{rel.emotional_valence:+.1f}" if rel.emotional_valence != 0 else ""
                parts.append(f"  {name}: {rel.impression} {trust_str} {emo_str}".strip())

        if self.short_term.short_term_goals:
            parts.append(f"【当前目标】{'；'.join(self.short_term.short_term_goals)}")

        return "\n".join(parts)
