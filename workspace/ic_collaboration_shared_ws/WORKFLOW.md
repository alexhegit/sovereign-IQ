# IC 协作共享工作区 - 标准工作流程

## 📁 目录结构

```
ic_collaboration_shared_ws/
├── WORKFLOW.md                 # 本文件
├── PROJECT_TEMPLATES/          # 项目底稿模板
│   ├── PROJECT_BRIEF_TEMPLATE.md    # 项目基础信息模板
│   ├── TEAM_PROFILE_TEMPLATE.md     # 团队画像模板
│   └── FINANCIAL_OVERVIEW_TEMPLATE.md # 财务概览模板
├── TASKS/                      # 当前任务目录
│   └── [任务 ID]/
│       ├── PROJECT_BRIEF.md        # 项目底稿
│       ├── TASK_CHECKLIST.md       # 任务检查清单
│       ├── R1_RAW_DATA.md          # R1 轮次原始数据
│       └── PUBLIC_INTEL/           # 秘书获取的公开信息
├── ARCHIVE/                    # 历史任务归档
└── INDEX.md                    # 任务索引
```

---

## 🔄 R1 轮次标准工作流程

### 1️⃣ **任务创建阶段**

**Step 1: 创建任务目录**
```bash
任务 ID: [YYYYMMDD-XXXX] (日期 - 序号)
示例：20260405-IC001
```

**Step 2: 秘书（Coordinator）准备项目底稿**
- 填写 `PROJECT_BRIEF.md`（项目基础信息）
- 填写 `TEAM_PROFILE.md`（团队背景）
- 填写 `FINANCIAL_OVERVIEW.md`（财务数据）

**Step 3: 上传至共享工作区**
```
位置：ic_collaboration_shared_ws/TASKS/[任务 ID]/
```

---

### 2️⃣ **Agent 接入阶段**

**每个 Agent 的任务：**

#### A. **读取项目底稿**
```bash
文件路径：/home/xsuper/.openclaw/workspace/ic_collaboration_shared_ws/TASKS/[任务 ID]/PROJECT_BRIEF.md
```

#### B. **检索私有知识库（Milvus）**
- **Collection ID**: `[Agent ID]` (如 `ic_strategist`)
- **检索范围**: 相关性排名前 20 的历史案例
- **检索内容**: 政策文件、资本流向、行业趋势、类似项目

**检索脚本示例：**
```python
# 伪代码
collection_id = "ic_strategist"
top_k = 20
query = "赛道配置建议 + 政策趋势 + 资金流向 + 经济周期"
results = milvus_search(collection=collection_id, query=query, top_k=top_k)
load_context(results)
```

#### C. **加载上下文并发表观点**
- 基于项目底稿
- 基于检索到的私有知识库内容
- 基于自身专业领域
- 发表 R1 轮次专业观点

#### D. **输出观点文件**
```bash
位置：/home/xsuper/.openclaw/workspace/ic_collaboration_shared_ws/TASKS/[任务 ID]/[agent_id]_view.md
```

---

### 3️⃣ **公开信息同步**

**秘书（Coordinator）的职责：**
- 获取公开信息（新闻、政策、行业报告）
- 整理后上传至 `PUBLIC_INTEL/` 目录
- 所有 Agent 实时可见

**文件格式：**
```
ic_collaboration_shared_ws/TASKS/[任务 ID]/PUBLIC_INTEL/
├── policy_updates.md
├── market_trends.md
├── competitor_analysis.md
└── public_news.md
```

---

## 📝 协作协议

### **数据一致性**
- ✅ 所有 Agent 读取同一份项目底稿
- ✅ 所有 Agent 可访问秘书上传的公开信息
- ✅ 每个 Agent 只读自己的私有知识库

### **输出标准**
- ✅ 使用 SIQ 标准模板
- ✅ 明确标注 Agent ID、轮次、时间戳
- ✅ 观点文件保存在任务目录下
- ✅ 观点文件标记为 SIQ 品牌

### **版本控制**
- ✅ 每个任务目录对应一个独立项目
- ✅ 完成后的任务归档至 `ARCHIVE/`
- ✅ 使用 Git 进行版本控制（如有需要）

---

## 🔧 工具使用

### **检索脚本自动化**

每个 Agent 应包含以下检索脚本（自动执行）：

```python
# Agent-specific search script
# Location: ~/.openclaw/workspace/[agent_id]_workspace/scripts/search.py

def search_my_knowledge(base_project_info, task_id):
    """
    基于项目信息，检索私有知识库
    """
    collection_id = "ic_strategist"  # 根据 Agent 自动替换
    top_k = 20
    
    # 构建查询
    query = build_query_from_project(base_project_info)
    
    # Milvus 检索
    results = milvus.search(
        collection=collection_id,
        query=query,
        top_k=top_k,
        output_fields=["content", "score", "metadata"]
    )
    
    # 加载上下文
    for result in results:
        print(f"Loading: {result['content'][:200]}...")
        load_as_context(result)
    
    return results
```

### **执行流程**

**在 Agent 启动时自动执行：**
```bash
# 1. 读取项目底稿
cat ic_collaboration_shared_ws/TASKS/[任务 ID]/PROJECT_BRIEF.md

# 2. 执行检索脚本
python ~/.openclaw/workspace/ic_strategist_workspace/scripts/search.py

# 3. 基于检索结果发表观点
```

---

## 📊 任务索引

### 当前活跃任务
| 任务 ID | 项目名 | 状态 | 创建时间 |
|--------|-------|------|---------|
| 20260405-IC001 | TEST_2026 | R1 | 2026-04-05 16:39 |

### 历史归档
| 任务 ID | 项目名 | 完成轮次 | 归档时间 |
|--------|-------|---------|---------|
| [查看 ARCHIVE/](./ARCHIVE/) | | | |

---

## 🚀 快速启动命令

**1. 创建新任务目录：**
```bash
mkdir ic_collaboration_shared_ws/TASKS/[任务 ID]
```

**2. 准备项目底稿（秘书）：**
```bash
cp PROJECT_TEMPLATES/PROJECT_BRIEF_TEMPLATE.md TASKS/[任务 ID]/PROJECT_BRIEF.md
# 编辑填充项目信息
```

**3. Agent 自动加载（每个 Agent）：**
```bash
cd ~/.openclaw/workspace/ic_collaboration_shared_ws/TASKS/[任务 ID]
# 读取底稿 → 检索知识库 → 发表观点
```

---

## 📌 注意事项

1. **项目底稿必须完整**：Agent 需要足够的信息才能发表专业观点
2. **检索结果需明确标注**：每个 Agent 应标注检索到了哪些历史案例
3. **公开信息及时同步**：秘书应在 Agent 开始前完成公开信息上传
4. **观点文件格式统一**：使用 SIQ 标准模板
5. **版本控制**：完成后的任务应归档到 ARCHIVE/

---

_此文件由 SIQ 投委会 Coordinator 维护，确保所有 Agent 遵循统一的工作流程。_
