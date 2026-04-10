# SOVEREIGN-IQ Unified Retriever 技能

## 技能名称
`unified-retriever` - 统一检索技能

## 功能定位
跨库、跨模态的"全知雷达"，支撑主席Agent跨越项目事实与专家经验进行深度检索。

## 核心能力

### 1. 联邦检索
单次Query同时穿透多个Collection：
- 共享库（事实+观点）
- 私有库（专家方法论）
- 归档库（历史经验）

### 2. 标量-向量复合检索
- 通过project_tag进行毫秒级预过滤
- 向量相似度精准匹配
- 双重保障，检索又快又准

### 3. 多种检索范围

| 范围 | 说明 | 适用场景 |
|------|------|---------|
| `CURRENT_PROJECT` | 当前项目 | 只看当前项目的事实和观点 |
| `EXPERT_PRIVATE` | 专家私有库 | 只看方法论 |
| `ARCHIVE` | 历史归档 | 看历史项目经验 |
| `FULL_SPECTRUM` | 全谱检索 | 主席全知视角 |

## 脚本位置
```
ic_master_coordinator_workspace/scripts/
├── project_ingestor.py      # 底稿入库
├── secretary_supplement.py    # 情报补充
├── evolution_recorder.py     # 观点记录
└── unified_retriever.py     # 统一检索 ⭐
```

## 使用方法

### 方式1：命令行检索
```bash
python3 ic_master_coordinator_workspace/scripts/unified_retriever.py
```

### 方式2：API调用
```python
from unified_retriever import UnifiedRetriever

retriever = UnifiedRetriever()

# 当前项目检索
results = retriever.search_current_project(
    query="该公司的估值是否合理？",
    project_tag="YUSHU_2026"
)

# 专家方法论检索
results = retriever.search_methodology(
    query="如何评估研发驱动型初创公司？",
    expert_filter=["ic_finance_auditor", "ic_sector_expert"]
)

# 全谱检索（主席全知视角）
results = retriever.search_full_spectrum(
    query="类似项目有哪些风险点可以借鉴？",
    project_tag="YUSHU_2026"
)

# 格式化输出
print(retriever.format_results(results))

retriever.close()
```

## 检索模式

| 模式 | 方法 | 说明 |
|------|------|------|
| 当前项目 | `search_current_project()` | 只看当前项目的共享库 |
| 专家方法论 | `search_methodology()` | 只看专家私有库 |
| 历史归档 | `search_archive()` | 只看归档库 |
| 全谱检索 | `search_full_spectrum()` | 看所有库（主席全知） |

## 检索结果结构

```python
SearchResult:
    content: str          # 内容
    source: str           # 来源Collection
    source_type: str      # shared/archive/private
    agent_id: str        # 来源Agent
    project_tag: str     # 项目标签
    score: float         # 相似度分数
    knowledge_type: str  # methodology/fact/discussion
    metadata: Dict       # 完整元数据
```

## 检索结果展示

```
======================================================================
🔍 检索结果 (5 条)
======================================================================

──────────────────────────────────────────────────────────────────────
1. 📋 共享库 [ic_finance_auditor] ✨ 方法论
   项目: YUSHU_2026
   分数: 0.9523
   内容: 对于研发驱动型初创公司，评估其价值时应采用'市研率'指标...

──────────────────────────────────────────────────────────────────────
2. 🔐 私有库 [ic_sector_expert] ✨ 方法论
   项目: YUSHU_2026
   分数: 0.8945
   内容: 人形机器人行业的市场规模测算应采用'设备数量×单价'的Bottom-up方法...

──────────────────────────────────────────────────────────────────────
3. 📦 归档库 [] 📄 事实
   项目: XINGTU_2025
   分数: 0.8234
   内容: 该项目在2025年Q2出现现金流断裂风险，原因是...

======================================================================
```

## Collection映射

| Collection | 名称 | 类型 |
|-----------|------|------|
| `ic_collaboration_shared_ws` | 协同共享库 | shared |
| `ic_archive_sop_ws` | 归档库 | archive |
| `ic_chairman_ws` | 主席私有库 | private |
| `ic_finance_auditor_ws` | 财务专家库 | private |
| `ic_legal_scanner_ws` | 法律专家库 | private |
| `ic_risk_controller_ws` | 风控专家库 | private |
| `ic_sector_expert_ws` | 行业专家库 | private |
| `ic_strategist_ws` | 战略专家库 | private |
| `ic_master_coordinator_ws` | 秘书库 | private |

## 主席全知视角

```
全谱检索 = 当前项目事实 + 当前项目观点 + 专家方法论 + 历史归档
                    ↓
              主席获得全局视角
                    ↓
         不遗漏任何有价值的信息
```

## 去重机制

- 基于内容前100字符去重
- 避免重复结果
- 保留最高score的结果

## 注意事项

1. 确保向量化服务（localhost:8000）正常运行
2. 确保Milvus各Collection已初始化
3. 全谱检索可能较慢，建议指定项目标签
