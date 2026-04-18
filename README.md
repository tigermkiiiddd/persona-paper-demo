# Persona Deduction Theater — Paper Demo

> 论文《规则通用，数值驱动，涌现结果：一个活生生的数字人沙盒的理论与实践》配套可复现代码。

## 核心概念

- **20维本我向量**：每个维度有当前值/基线值/敏感度/衰减速率，动态内稳态系统
- **统一信息输入**：万物皆事件（类型/强度/效价/持续性）
- **感知过滤**：150°视锥 + 全向耳朵 + 触觉，物理约束创造信息差
- **因果引擎**：22条因果边，方向和权重因人而异
- **驱动力涌现**：5类二级驱动 × 阈值判定 = 主观能动性
- **天道系统**：规则库 + LLM法则生成，世界从死到活

## 快速开始

```bash
# 安装依赖
pip install pydantic>=2.0 openai>=1.0

# 配置 .env
cp .env.example .env
# 编辑 .env 填入你的 OPENAI_API_KEY 和 OPENAI_BASE_URL

# 运行竹林茶馆 demo（LLM驱动）
python demo_v3.py

# 运行完整同步模拟
python demo_full.py
```

## Demo 说明

| 脚本 | 说明 |
|------|------|
| `demo_v3.py` | Simulation引擎 + LLM行为生成，竹林茶馆追兵场景 |
| `demo_full.py` | 完整时间切片同步模拟，所有角色同时接收广播 |
| `demo_scene.py` | 竹林茶馆10切片完整故事 |

## 项目结构

```
src/pdt/
├── core/          # 核心数据模型
│   ├── vector.py      # 20维本我向量 + 子维度 + Buff
│   ├── character.py   # 角色（集成全部子系统）
│   ├── memory.py      # 记忆层（长期+短期）
│   ├── event.py       # 事件结构 + 维度影响映射
│   ├── causal.py      # 因果引擎（22条边）
│   ├── perception.py  # 感知器官（视锥/听觉/触觉）
│   ├── spatial.py     # 空间坐标 + 世界事件
│   ├── scene.py       # 场景系统
│   ├── body.py        # 身体状态（HP/心率/肢体）
│   ├── behavior.py    # 结构化行为输出
│   └── timeslice.py   # 时间切片（12级叙事节奏）
├── engine/        # 模拟引擎
│   ├── simulation.py  # 沙盒核心
│   ├── tools.py       # 工具定义（speak/act/think/feel/attack/...）
│   ├── executor.py    # 工具执行器
│   └── judge.py       # 世界判定系统 + 天道
└── llm/           # LLM行为生成
    ├── behavior.py    # Tool Calling行为生成器
    └── tiandao.py     # 天道系统
```

## 论文引用

```
@article{pdt2026,
  title={规则通用，数值驱动，涌现结果：一个活生生的数字人沙盒的理论与实践},
  author={Persona Deduction Theater Project},
  journal={S.H.I.T Journal},
  year={2026}
}
```

## License

MIT
