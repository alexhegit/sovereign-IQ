# IC_Master_Coordinator 技能调用配置

## 核心技能

### 1. project_ingestor（底稿入库）
供人类用户将项目底稿入库至协同共享库。

**调用示例：**
```python
from scripts.project_ingestor import ProjectIngestor

ingestor = ProjectIngestor()
result = ingestor.ingest(
    file_path="path/to/底稿.pdf",
    project_tag="YUSHU_2026",
    source="human"
)

# 人类确认后入库
if human_confirm():
    ingestor.commit_to_milvus(result)
```

### 2. unified_data_fetcher（统一数据获取）
整合企查查 + Tavily + Exa 三源数据获取。

**调用示例：**
```python
from scripts.unified_data_fetcher import UnifiedDataFetcher

fetcher = UnifiedDataFetcher()
data = fetcher.fetch_company_data(
    company_name="宇树科技",
    credit_code="9133XXXXXXXX"
)

# 输出：
{
    "company_name": "宇树科技",
    "official_data": {...},           # 企查查官方数据
    "public_data_tavily": {...},       # Tavily公开信息
    "public_data_exa": {...},          # Exa深度信息
    "data_sources": ["qcc", "tavily", "exa"],
    "data_completeness": 1.0           # 数据完整度
}
```

**数据获取策略：**
| 数据源 | 优先级 | 内容类型 | 延迟 |
|--------|--------|----------|------|
| 企查查API | P0 | 官方工商/风险/知识产权/经营 | <2s |
| TavilyAPI | P1 | 新闻/融资/行业动态 | <1s |
| ExaAPI | P2 | 深度文章/技术文档 | <3s |

**API配置：**
- 企查查API：`config/qcc_mcp_config.json`
- TavilyAPI：`config/.env` (TAVILY_API_KEY)
- ExaAPI：`config/.env` (EXA_API_KEY)

### 3. evolution_recorder（观点记录）
记录Agent三轮讨论观点，管理知识沉淀。

### 4. report_generator（报告生成）
整合所有专家观点生成IC决策报告。

---

## API客户端列表

| 客户端 | 功能 | 配置位置 | 状态 |
|--------|------|----------|------|
| `qcc_client.py` | 企查查API（工商、风险、知识产权、经营） | `config/qcc_mcp_config.json` | ✅ 已配置 |
| `tavily_client.py` | Tavily搜索（快速公开信息） | `config/.env` | ✅ 已配置 |
| `exa_client.py` | Exa搜索（深度内容提取） | `config/.env` | ✅ 已配置 |
| `unified_data_fetcher.py` | 统一数据获取（整合三源） | 自动加载上述配置 | ✅ 已创建 |

---

## 数据获取流程

```python
# 步骤1: 人类上传底稿 → 解析入库
project = project_ingestor.ingest(...)

# 步骤2: 并行调用三源API获取数据
data = unified_data_fetcher.fetch_company_data(...)
#  - 企查查：官方工商、风险、知识产权、经营信息
#  - Tavily：快速公开信息、新闻、融资动态
#  - Exa：深度文章、技术文档、竞品分析

# 步骤3: 生成信息质量评分卡
score_card = generate_quality_score(data)
#  L4可信 / L3可靠 / L2存疑 / L1危险

# 步骤4: 差异分析（如有冲突，提示人类决策）
conflicts = compare_with_base(project, data)
if conflicts:
    human_decision = prompt_human("Y继续/N暂停")

# 步骤5: 分发给各专家Agent
schedule_experts(project_tag, data)
```

---

## 数据质量评估

### L4 - 可信（差异=0）
- 企查查官方数据完整
- 三源信息一致
- → 直接进入尽调

### L3 - 可靠（低严重度差异≤2）
- 主要信息一致，细节有出入
- → 标注后进入尽调

### L2 - 存疑（低严重度差异>2）
- 信息有矛盾，需进一步核实
- → 谨慎进入，补充采集

### L1 - 危险（高严重度差异≥1）
- 重大信息冲突或缺失
- → 暂停+澄清请求

---

## 红线（禁止事项）

❌ 不做具体财务计算（Finance Auditor负责）
❌ 不做法律合规判断（Legal Scanner负责）
❌ 不做风险评估（Risk Controller负责）
❌ 不做战略方向判断（Strategist负责）
❌ 不做行业技术分析（Sector Expert负责）
❌ 不做最终投资决策（Chairman负责）
❌ **不代替人类决策**（人类有最终决策权）

---

This agent operates as part of the SIQ Investment Committee framework.
Orchestration excellence is key to efficient decision-making.