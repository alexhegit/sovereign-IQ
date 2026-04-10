<div align="center">

# Sovereign-IQ

**AI 多 Agent 智能投研决策系统**

面向中国一级市场的投资委员会模拟系统 —— 7 个专业化 AI Agent 协同尽调、对抗论证、知识沉淀

![1](./pics/1.png)

## 核心特色

**对抗式多轮论证** —— R1 独立分析 → R2 交叉质证 → R3 红蓝对抗，三轮递进消除信息盲区与群体思维

**知识结晶与进化** —— 每次投委会讨论中的高价值洞察自动提取并回流至专家私有知识库，形成组织记忆

**全链路可审计** —— 从文档摄入到最终决策，完整记录推理链路、证据来源与观点演变过程

**人机主权决策** —— AI 提供结构化分析框架与证据支撑，人类保留最终决策权，不替代判断

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Master Coordinator                    │
│              (流程编排 · 进度追踪 · 报告聚合)              │
├─────────┬──────────┬──────────┬──────────┬──────────────┤
│Strategist│Sector    │Finance   │Legal     │Risk          │
│宏观策略   │行业分析   │财务审计   │法务合规   │风控评估       │
├─────────┴──────────┴──────────┴──────────┴──────────────┤
│                     IC Chairman                          │
│               (综合裁决 · Go/No-Go 决策)                  │
├─────────────────────────────────────────────────────────┤
│              Milvus 向量知识库 (9 集合)                    │
│    专家私有库 × 7  ·  协作共享库 × 1  ·  归档库 × 1        │
└─────────────────────────────────────────────────────────┘
```

---

## 投委会流程

| 阶段 | 内容 | 产出 |
|------|------|------|
| **文档摄入** | 自动解析 PDF/DOCX/MD，向量化存入专家私有知识库 | 项目知识底座 |
| **R1 独立尽调** | 5 位专家并行分析，六维评分（赛道β、公司α、行业地位、法律合规、估值风险、技术壁垒） | 各领域独立报告 |
| **R2 交叉质证** | 针对争议点补充论证，修正风险评估 | 更新报告 + 争议消解 |
| **R3 红蓝对抗** | 红蓝双方压力测试核心假设，推演极端情景 | 风险概率调整 + 严苛条件 |
| **主席裁决** | 综合定量（30%）与定性（70%），输出投资建议 | IC 决策报告 |

---

## Agent 角色定义

| Agent | 职责 | 核心能力 |
|-------|------|----------|
| **IC Chairman** | 最终裁决与冲突仲裁 | 六维评估框架、Go/No-Go 决策树、退出策略评估 |
| **Strategist** | 宏观政策解读、资本流向、赛道配置 | 政策影响评估、经济周期匹配、赛道吸引力评分 |
| **Sector Expert** | 行业深度分析、技术路线评估 | TAM/SAM/SOM 测算、波特五力、技术成熟度曲线 |
| **Finance Auditor** | 财务建模、估值验证、真实性核查 | 多阶段估值模型（Berkus/VC/DCF）、FIRE 诊断、压力测试 |
| **Legal Scanner** | 合规审查、诉讼穿透、条款风险评估 | 50+ 项尽调清单、合规指数量化、红线问题识别 |
| **Risk Controller** | 风险量化、舆情监控、红黄线判定 | 风险评分模型（0-100）、多情景生存分析、ESG 评估 |
| **Master Coordinator** | 流程编排、数据交叉验证、审计链生成 | 并行尽调调度、三源数据整合（QCC+Tavily+Exa） |

---

## 模型配置

项目按角色分配不同规模的推理模型，实现算力与能力的精准匹配：

| Agent | 推理模型 | 向量模型 |
|-------|----------|----------|
| **IC Chairman** | Nemotron-120B | Qwen3-VL-Embedding-2B (2048 维) |
| **Finance Auditor** | Nemotron-120B | Qwen3-VL-Embedding-2B (2048 维) |
| **Sector Expert** | Nemotron-120B | Qwen3-VL-Embedding-2B (2048 维) |
| **Legal Scanner** | Qwen3-32B | Qwen3-VL-Embedding-2B (2048 维) |
| **Strategist** | Qwen3-32B | Qwen3-VL-Embedding-2B (2048 维) |
| **Risk Controller** | Qwen3-32B | Qwen3-VL-Embedding-2B (2048 维) |
| **Master Coordinator** | Qwen3-32B | Qwen3-VL-Embedding-2B (2048 维) |

> 所有模型均通过 Ollama 本地部署，Nemotron-120B 驱动核心决策角色（主席/财务/行业），Qwen3-32B 驱动支持角色（法务/战略/风控/协调），向量模型统一采用 Qwen3-VL-Embedding-2B Q8_0 量化。

---

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| **推理模型** | Nemotron-Cascade-2-30B-A3B、Qwen3-32B（Ollama 本地部署） |
| **向量模型** | Qwen3-VL-Embedding-2B（vllm) |
| **向量数据库** | Milvus（HNSW / GPU_CAGRA 索引） |
| **GPU 加速** | CuPy 向量运算、异步并发注入 |
| **文档解析** | PyMuPDF（空间 PDF 解析）、python-docx |
| **数据源** | AkShare、Tavily、Exa、QCC |

---

## 知识管线

```
1#env_setup.py            初始化 Milvus 集合与索引
2#knowledge_feeder.py     GPU 加速批量知识注入
3#project_ingestor.py     多格式文档自动处理（状态机：incoming → processed/failed）
4#evolution_recorder.py   讨论记录 + 知识结晶（双存储：共享库 + 私有库）
5#unified_retriever.py    跨集合联邦检索 + 证据链构建
6#archive_manager.py      已完结项目归档 + 存储空间自愈
7#knowledge_ingestor_pro.py  异步多格式高并发注入引擎
```

---

## 项目结构

```
sovereign-IQ/
├── milvus_knowlege_setup/        # 知识管线脚本
│   ├── 1#env_setup.py
│   ├── 2#knowledge_feeder.py
│   ├── 3#project_ingestor.py
│   ├── 4# evolution_recorder.py
│   ├── 5# unified_retriever.py
│   ├── 6# archive_manager.py
│   └── 7#knowledge_ingestor_pro.py
├── workspace/                    # Agent 工作空间
│   ├── ic_chairman_workspace/
│   ├── ic_finance_auditor_workspace/
│   ├── ic_sector_expert_workspace/
│   ├── ic_legal_scanner_workspace/
│   ├── ic_strategist_workspace/
│   ├── ic_risk_controller_workspace/
│   ├── ic_master_coordinator_workspace/
│   ├── skills/                   # 39 个专业技能定义
│   └── connect_existing_collections.py
├── 测试案例生成报告供参考/         # 宇树机器人多轮对抗测试报告
├── 部分调研资料/                      # 调研资料
├── SIQ_系统介绍_技术文档.pdf
└── TODO.md
```

---

## License

See [LICENSE](LICENSE).
