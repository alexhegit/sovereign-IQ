# SOVEREIGN-IQ Archive & Self-Healing Manager 技能

## 技能名称
`archive-manager` - 结项归档与空间自愈技能

## 功能定位
项目结束后的数据生命周期管理，确保数据有序归档并释放共享空间。

## 核心能力

### 1. 数据迁移
将指定项目标签的所有向量及元数据从"协同共享库"搬迁至"历史归档库"

### 2. 空间自愈
物理删除共享库中的旧数据后，触发Milvus空间回收与索引重构

### 3. 知识资产化
生成结项审计日志，完成从"过程数据"到"数字资产"的转化

## 脚本位置
```
ic_master_coordinator_workspace/scripts/
├── project_ingestor.py         # 底稿入库
├── secretary_supplement.py     # 情报补充
├── evolution_recorder.py      # 观点记录
├── unified_retriever.py      # 主席检索
└── archive_manager.py       # 归档管理 ⭐
```

## 使用方法

### 方式1：命令行交互
```bash
python3 ic_master_coordinator_workspace/scripts/archive_manager.py
```

### 方式2：API调用
```python
from archive_manager import SovereignArchiver

# 初始化
archiver = SovereignArchiver()

# 执行归档
archiver.migrate_project_data("YUSHU_2026")

# 查询归档数据
results = archiver.query_archive("YUSHU_2026")

# 获取统计
stats = archiver.get_statistics()

archiver.close()
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 查询                                               │
│ 从共享库查询该项目的所有数据                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 迁移（Transactional Migration - 先写后删）        │
│ 分批写入归档库，确保数据不丢失                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 清理（Space Self-Healing）                        │
│ 物理删除共享库中的旧数据                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 空间自愈                                          │
│ 重建归档库索引，优化存储结构                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 资产凭证化                                         │
│ 生成带血缘追踪的JSON归档报告                              │
└─────────────────────────────────────────────────────────────┘
```

## 归档报告结构

```json
{
  "project_tag": "YUSHU_2026",
  "archive_time": "2026-04-02T10:45:00",
  "entities_moved": 50,
  "entities_deleted": 50,
  "status": "COMPLETED",
  "source": "ic_collaboration_shared_ws",
  "destination": "ic_archive_sop_ws",
  "batch_count": 1,
  "lineage_records": [
    {
      "entity_id": 123,
      "source_project_tag": "YUSHU_2026",
      "source_collection": "ic_collaboration_shared_ws",
      "content_preview": "该公司2024年营收3.92亿元...",
      "agent_id": "ic_finance_auditor",
      "round_num": 3,
      "knowledge_type": "methodology",
      "migrated_at": "2026-04-02T10:45:00"
    }
  ]
}
```

## 设计亮点

### 1. Transactional Migration（事务迁移）
先写后删，确保数据不丢失

### 2. Batch Processing（分批处理）
应对大规模项目底稿的搬迁压力
- 默认批次大小：500条
- 可配置

### 3. 空间自愈（Self-Healing）
物理删除后重建索引，保持系统性能

### 4. 资产凭证化
生成可追溯的JSON归档报告

## Collection配置

| Collection | 用途 | 操作 |
|-----------|------|------|
| `ic_collaboration_shared_ws` | 协同共享库 | 源库（读取+删除） |
| `ic_archive_sop_ws` | 历史归档库 | 目标库（写入） |

## 注意事项

1. **归档前请确认**：数据已完整迁移到归档库
2. **二次确认**：删除操作不可逆，请谨慎确认
3. **分批处理**：大批量数据会分批迁移，请耐心等待
4. **空间自愈**：索引重建可能耗时较长
5. **归档报告**：保存在 `archives/` 目录

## 命令行示例

```
$ python3 scripts/archive_manager.py

============================================================
📦 Sovereign-IQ | 项目结项归档与空间自愈管理器 v2.0
============================================================

💡 功能说明:
   1. 数据迁移：协同共享库 → 历史归档库
   2. 空间自愈：物理删除后重建索引
   3. 资产凭证化：生成JSON归档报告

🏷️ 请输入要归档结项的项目标签 (Project Tag): YUSHU_2026

⚠️ 警告：此操作将把项目数据从共享库迁移至归档库！
❓ 确定要将项目 [YUSHU_2026] 归档吗？(y/n): y

[Step 1/5] 查询项目数据...
   🔍 检索到 50 条数据片段，准备搬迁
[Step 2/5] 迁移数据到归档库...
   ✅ 批次 1: 已迁移 50 条
   ✅ 成功将 50 条数据同步至归档库
[Step 3/5] 清理共享库...
   ✅ 共享库空间自愈完成
[Step 4/5] 执行空间自愈...
   🔧 正在重建索引...
   ✅ 归档库索引重建完成
[Step 5/5] 生成归档凭证...
      ✅ 归档报告已生成

============================================================
✨ 归档完成!
   项目: YUSHU_2026
   迁移: 50 条
   删除: 50 条
   批次: 1
   报告: archives/archive_log_YUSHU_2026_20260402_104500.json
============================================================
```
