# SOVEREIGN-IQ Evolution Recorder 技能

## 技能名称
`evolution-recorder` - 决策进化记录技能

## 功能定位
记录Agent在投决会中的观点，实现"知识分流"：
- 所有观点存入共享库（全局可见）
- 第二轮、第三轮观点回传私有库（能力进化）

**所有Agent都要使用此技能**

## 核心逻辑

```
Agent发表观点
       ↓
  ┌───┴───┐
  ↓       ↓
 第一轮   第二/三轮
  ↓       ↓
共享库   共享库 + 私有库
        ↓
     自动触发
     去重检查
        ↓
     ┌──┴──┐
     ↓     ↓
   已存在  不存在
     ↓     ↓
   跳过   写入
```

## 脚本位置
```
ic_master_coordinator_workspace/scripts/
├── project_ingestor.py      # 底稿入库
├── secretary_supplement.py    # 情报补充
└── evolution_recorder.py    # 观点记录 ⭐
```

## 使用方法

### 方式1：命令行演示
```bash
python3 ic_master_coordinator_workspace/scripts/evolution_recorder.py
```

### 方式2：API调用
```python
from evolution_recorder import EvolutionRecorder

recorder = EvolutionRecorder()

# 第一轮
recorder.record_round1("ic_finance_auditor", "YUSHU_2026", "观点内容...")

# 第二轮
recorder.record_round2("ic_finance_auditor", "YUSHU_2026", "完善后的观点...")

# 第三轮（自动触发私有库回传）
recorder.record_round3("ic_finance_auditor", "YUSHU_2026", "方法论总结...")

recorder.close()
```

## 核心接口

| 接口 | 说明 | 存储目标 |
|------|------|---------|
| `record_round1()` | 第一轮观点 | 共享库 |
| `record_round2()` | 第二轮观点 | 共享库 + 私有库 |
| `record_round3()` | 第三轮观点 | 共享库 + 私有库 |
| `record()` | 通用接口 | 可配置 |

## 元数据结构

### 共享库存档
```python
{
    "viewpoint_id": "uuid-xxx",
    "agent_id": "ic_finance_auditor",
    "project_tag": "YUSHU_2026",
    "round": 3,
    "viewpoint_type": "red_blue",
    "content": "完整观点内容",
    "reference_viewpoints": ["vid1", "vid2"],
    "is_methodology": True,
    "timestamp": "2026-04-02T...",
    "source": "evolution_recorder"
}
```

### 私有库存档
```python
{
    "knowledge_type": "methodology",
    "source_project": "YUSHU_2026",
    "source_viewpoint_id": "uuid-xxx",
    "round": 3,
    "agent_id": "ic_finance_auditor",
    "crystallized_at": "2026-04-02T...",
    "content": "方法论内容",
    "content_hash": "abc123..."  # 用于去重
}
```

## 去重机制

基于内容Hash的去重：
- 同一Agent的相似内容会被识别
- 已回传过的方法论不会重复写入
- 缓存在本地 `.evolution_dedup_cache.json`

## 存储目标

| Collection | 内容 | 性质 |
|-----------|------|------|
| `ic_collaboration_shared_ws` | 所有观点（1/2/3轮） | 全局可见 |
| `ic_finance_auditor_ws` | 财务专家的方法论 | 私有进化 |
| `ic_legal_scanner_ws` | 法律专家的方法论 | 私有进化 |
| `ic_risk_controller_ws` | 风控专家的方法论 | 私有进化 |
| `ic_sector_expert_ws` | 行业专家的方法论 | 私有进化 |
| `ic_strategist_ws` | 战略专家的方法论 | 私有进化 |
| `ic_chairman_ws` | 主席的方法论 | 私有进化 |
| `ic_master_coordinator_ws` | 秘书的方法论 | 私有进化 |

## 知识分流

| 内容 | 去向 | 触发 |
|------|------|------|
| 底稿 | 共享库 | 人类上传 |
| 第一轮观点 | 共享库 | Agent主动 |
| 第二轮观点 | 共享库 + 私有库 | Agent主动 |
| 第三轮观点 | 共享库 + 私有库 | 第三轮自动 |

## 使用Agent

**所有投委会成员都需要使用此技能：**

| Agent | ID | 用途 |
|-------|-----|------|
| 财务专家 | `ic_finance_auditor` | 记录财务观点 |
| 法律专家 | `ic_legal_scanner` | 记录法律观点 |
| 风控专家 | `ic_risk_controller` | 记录风控观点 |
| 行业专家 | `ic_sector_expert` | 记录行业观点 |
| 战略专家 | `ic_strategist` | 记录战略观点 |
| 主席 | `ic_chairman` | 记录决策观点 |
| 秘书 | `ic_master_coordinator` | 记录协调观点 |

1. 确保向量化服务（localhost:8000）正常运行
2. 确保Milvus各Collection已初始化
3. 去重缓存文件 `.evolution_dedup_cache.json` 需保留
