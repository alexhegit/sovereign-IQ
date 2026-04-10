# SOVEREIGN-IQ Chairman Retriever 技能

## 技能名称
`chairman-retriever` - 主席全知检索与投决报告生成技能

## 功能定位
**主席专用技能**，支撑主席跨越项目事实与专家经验进行深度检索，并生成包含各角色最终发言概况的高质量投决报告。

## 发言顺序（由秘书协调）

| 顺序 | 角色 | 职责 |
|------|------|------|
| 1 | **战略专家** | 宏观战略、政策导向、资金流向、赛道配置 |
| 2 | 行业专家 | 行业分析、市场规模、竞争格局、技术路线 |
| 3 | 财务专家 | 财务分析、估值模型、现金流 |
| 4 | 法律专家 | 法律合规、股权结构、监管合规 |
| 5 | 风控专家 | 风险评估、ESG、舆情、供应链 |
| 6 | **主席** | 综合各方意见，给出最终决策 |

## 报告结构

```
🏛️ SIQ 投决报告
│
├── 👥 各角色最终发言概况
│   ├── 第一轮发言（看完底稿）
│   ├── 第二轮发言（看完其他观点）
│   └── 第三轮发言（红蓝对抗）
│
├── 📋 各角色最终总结
│
├── 🏛️ 主席最终决策  ← 核心输出
│   ├── 各角色发言统计
│   ├── 综合意见摘要
│   └── 最终决策
│
└── 📑 详细证据链
```

## 脚本位置
```
ic_master_coordinator_workspace/scripts/
├── project_ingestor.py      # 底稿入库
├── secretary_supplement.py    # 情报补充
├── evolution_recorder.py     # 观点记录
└── unified_retriever.py     # 主席检索 ⭐
```

## 使用方法

### 方式1：命令行交互
```bash
python3 ic_master_coordinator_workspace/scripts/unified_retriever.py
```

### 方式2：API调用
```python
from unified_retriever import ChairmanRetriever

retriever = ChairmanRetriever()

# 1. 全库穿透检索
results = retriever.search_all(
    query="该项目的核心风险点是什么？",
    project_tag="YUSHU_2026",
    top_k=10
)

# 2. 构建证据链
chains = retriever.build_evidence_chains(results)
for chain in chains:
    print(f"\n【{chain.dimension}】")
    for item in chain.items:
        print(f"  • {item.content[:80]}...")

# 3. 生成完整投决报告
queries = {
    "executive": "项目概述、核心亮点",
    "financial": "财务状况、估值分析",
    "legal": "法律合规、股权结构",
    "risk": "主要风险点",
    "industry": "行业分析",
    "strategy": "战略建议"
}
report = retriever.generate_ic_report("YUSHU_2026", queries)
print(retriever.format_report(report))

retriever.close()
```

## 主席检索模式

| 模式 | 说明 | 检索范围 |
|------|------|---------|
| `search_all()` | 全库穿透 | 所有库 |
| `search_current()` | 当前项目 | 共享库+归档库 |
| `search_methodology()` | 方法论 | 仅专家私有库 |
| `generate_ic_report()` | 生成报告 | 全部维度 |

## 证据链结构

```python
EvidenceChain:
    dimension: str       # 维度（财务/法律/风险/行业/战略）
    evidence_type: str  # 类型（fact/methodology/discussion）
    items: List[SearchResult]  # 证据列表
    summary: str        # 证据摘要
```

## 角色发言结构

```python
RoleViewpoint:
    agent_id: str            # Agent ID
    role_name: str           # 角色名称
    focus: str             # 关注重点
    round1_content: str     # 第一轮发言
    round2_content: str     # 第二轮发言
    round3_content: str     # 第三轮发言
    final_summary: str      # 最终总结
```

## 投决报告结构

```python
ICReport:
    project_tag: str           # 项目标签
    generated_at: str         # 生成时间
    role_viewpoints: List[RoleViewpoint]  # 各角色最终发言
    chairman_decision: str      # 主席最终决策
    evidence_chains: List[EvidenceChain]  # 证据链
```

## 检索结果展示

```
======================================================================
🏛️ SIQ 投决报告
======================================================================
项目: YUSHU_2026
生成时间: 2026-04-02T10:30:00

======================================================================
👥 各角色最终发言概况
======================================================================
发言顺序:
  1. 战略专家 - 宏观战略、政策导向、资金流向、赛道配置
  2. 行业专家 - 行业分析、市场规模、竞争格局、技术路线
  3. 财务专家 - 财务分析、估值模型、现金流
  4. 法律专家 - 法律合规、股权结构、监管合规
  5. 风控专家 - 风险评估、ESG、舆情、供应链
  6. 主席 - 综合各方意见，给出最终决策

──────────────────────────────────────────────────────────────────────
📤 第一轮发言（看完底稿）
──────────────────────────────────────────────────────────────────────
【行业专家】
  人形机器人市场2025年预计突破300亿元...

【战略专家】
  政策利好频出，十四五规划明确支持...

──────────────────────────────────────────────────────────────────────
📤 第二轮发言（看完其他观点）
──────────────────────────────────────────────────────────────────────
【财务专家】
  补充：估值偏高，但考虑到技术壁垒可接受...

──────────────────────────────────────────────────────────────────────
📤 第三轮发言（红蓝对抗）
──────────────────────────────────────────────────────────────────────
【行业专家】
  总结：行业确定性强，但竞争加剧需注意...

======================================================================
🏛️ 主席最终决策
======================================================================
【各角色发言统计】
  • 行业专家: R1+R2+R3
  • 战略专家: R1+R2+R3
  • 财务专家: R1+R2+R3
  • 法律专家: R1+R2
  • 风控专家: R1+R2
  • 主席: R1+R2

【最终决策】
  ✅ 建议推进：经过充分讨论，建议进入下一阶段尽调

  主席签字: _____________  日期: 2026-04-02
```

## Collection映射

| Collection | 用途 | 检索 |
|-----------|------|------|
| `ic_collaboration_shared_ws` | 项目事实+观点 | ✅ |
| `ic_archive_sop_ws` | 历史归档 | ✅ |
| `ic_chairman_ws` | 主席方法论 | ✅ |
| `ic_finance_auditor_ws` | 财务方法论 | ✅ |
| `ic_legal_scanner_ws` | 法律方法论 | ✅ |
| `ic_risk_controller_ws` | 风控方法论 | ✅ |
| `ic_sector_expert_ws` | 行业方法论 | ✅ |
| `ic_strategist_ws` | 战略方法论 | ✅ |
| `ic_master_coordinator_ws` | 秘书方法论 | ✅ |

## 证据链分组

| 维度 | 来源 | 类型 |
|------|------|------|
| 财务 | 财务专家库 | methodology/fact |
| 法律 | 法律专家库 | methodology/fact |
| 风险 | 风控专家库 | methodology/fact |
| 行业 | 行业专家库 | methodology/fact |
| 战略 | 战略专家库 | methodology/fact |
| 项目事实 | 共享库 | fact |
| 历史经验 | 归档库 | historical_lesson |

## 主席全知视角

```
全库穿透检索
      ↓
  证据链构建
      ↓
投决报告生成
      ↓
高质量决策支撑
```

## 注意事项

1. 确保向量化服务（localhost:8000）正常运行
2. 确保Milvus所有Collection已初始化
3. 全库检索可能耗时较长，建议设置合适的top_k
4. 投决报告生成依赖多维度检索，确保各库有足够数据
