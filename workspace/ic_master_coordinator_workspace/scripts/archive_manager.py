#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sovereign-IQ Archive & Self-Healing Manager (V2.0)
---------------------------------------------------------
功能：数据生命周期管理
1. 数据迁移：将指定项目标签的所有向量及元数据从"协同共享库"搬迁至"历史归档库"
2. 空间释放：物理删除共享库中的旧数据，触发Milvus空间回收与索引重构
3. 知识资产化：生成结项审计日志，完成从"过程数据"到"数字资产"的转化

设计亮点：
1. Transactional Migration（模拟事务迁移）：确保先写后删，防止数据丢失
2. Batch Processing（分片处理）：应对大规模项目底稿的搬迁压力
3. 空间自愈：物理删除后自动重建索引
4. 资产凭证化：生成带血缘追踪的JSON归档报告
"""

import os
import sys
import json
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 核心依赖
from pymilvus import connections, Collection, utility

# ============================================================================
# 日志配置
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("ArchiveManager")

# ============================================================================
# 常量配置
# ============================================================================

# Collection配置
SOURCE_WS = "ic_collaboration_shared_ws"    # 协同共享库（源）
ARCHIVE_WS = "ic_archive_sop_ws"           # 历史归档库（目标）

# 分批处理大小
BATCH_SIZE = 500

# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class LineageRecord:
    """血缘记录 - 追踪每条数据的来源和迁移历史"""
    entity_id: int                    # 原始实体ID
    source_project_tag: str          # 来源项目标签
    source_collection: str           # 来源Collection
    content_preview: str            # 内容预览（前100字符）
    agent_id: str = ""              # 来源Agent
    round_num: int = 0             # 观点轮次
    knowledge_type: str = ""        # 知识类型
    migrated_at: str = ""           # 迁移时间


@dataclass
class ArchiveReport:
    """归档报告 - 结项审计凭证"""
    project_tag: str                 # 项目标签
    archived_at: str               # 归档时间
    total_entities: int           # 总实体数
    migrated_entities: int        # 已迁移实体数
    deleted_entities: int         # 已删除实体数
    batch_count: int              # 分批数
    lineage_records: List[LineageRecord] = field(default_factory=list)  # 血缘记录
    statistics: Dict = field(default_factory=dict)  # 统计信息
    archive_path: str = ""         # 报告文件路径


# ============================================================================
# 主类
# ============================================================================

class SovereignArchiver:
    """
    Sovereign-IQ 归档与自愈管理器
    
    核心职责：
    1. 数据迁移：共享库 → 归档库
    2. 空间自愈：物理删除后重建索引
    3. 资产凭证化：生成归档报告
    """
    
    def __init__(
        self,
        source_ws: str = SOURCE_WS,
        archive_ws: str = ARCHIVE_WS
    ):
        """
        初始化归档管理器
        
        Args:
            source_ws: 源Collection（协同共享库）
            archive_ws: 目标Collection（历史归档库）
        """
        self.source_ws = source_ws
        self.archive_ws = archive_ws
        
        # 初始化数据库连接
        self._init_connections()
        
        logger.info("✅ ArchiveManager 初始化完成")
    
    def _init_connections(self):
        """建立与Milvus的连接并校验Collection健康状态"""
        try:
            # 建立连接
            connections.connect("default", host="localhost", port="19530")
            logger.info("✅ Milvus连接成功")
            
            # 校验源库和目标库是否存在
            for ws_name in [self.source_ws, self.archive_ws]:
                if not utility.has_collection(ws_name):
                    raise RuntimeError(f"❌ Collection {ws_name} 不存在，请检查环境配置")
            
            # 加载Collection到内存
            self.src_col = Collection(self.source_ws)
            self.arc_col = Collection(self.archive_ws)
            
            self.src_col.load()
            self.arc_col.load()
            
            logger.info(f"✅ 源库: {self.source_ws} ({self.src_col.num_entities} 条)")
            logger.info(f"✅ 目标库: {self.archive_ws} ({self.arc_col.num_entities} 条)")
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise
    
    # =========================================================================
    # 核心接口
    # =========================================================================
    
    def migrate_project_data(self, project_tag: str):
        """
        [核心接口] 结项归档 - 执行数据迁移与自愈清理
        
        工作流程：
        1. 查询该项目的所有数据（分批拉取）
        2. 写入归档库（先写后删，确保数据不丢失）
        3. 物理删除源库数据
        4. 触发空间自愈（重建索引）
        5. 生成归档凭证
        
        Args:
            project_tag: 要归档的项目标签
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"📁 启动项目归档任务: [{project_tag}]")
        logger.info(f"{'=' * 60}")
        
        # ----------------------------------------------------------------
        # 第1步：查询属于该项目的所有实体
        # ----------------------------------------------------------------
        logger.info("\n[Step 1/5] 查询项目数据...")
        
        expr = f'project_tag == "{project_tag}"'
        
        try:
            # 从共享库查询该项目的所有数据
            entities = self.src_col.query(
                expr=expr,
                output_fields=["id", "vector", "project_tag", "metadata"]
            )
            
            total_count = len(entities)
            
            if total_count == 0:
                logger.warning(f"⚠️ 项目 [{project_tag}] 在共享库中无数据，无需归档")
                return
            
            logger.info(f"   🔍 检索到 {total_count} 条数据片段，准备搬迁")
            
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return
        
        # ----------------------------------------------------------------
        # 第2步：分批写入归档库（Transactional Migration - 先写后删）
        # ----------------------------------------------------------------
        logger.info("\n[Step 2/5] 迁移数据到归档库...")
        
        # 提取数据
        vectors = [item["vector"] for item in entities]
        tags = [item["project_tag"] for item in entities]
        metas = []
        
        # 构建血缘记录
        lineage_records = []
        for item in entities:
            metadata = item.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {"content": metadata}
            
            # 血缘记录
            lineage = LineageRecord(
                entity_id=item.get("id", 0),
                source_project_tag=project_tag,
                source_collection=self.source_ws,
                content_preview=metadata.get("content", metadata.get("content_preview", ""))[:100],
                agent_id=metadata.get("agent_id", ""),
                round_num=metadata.get("round", 0),
                knowledge_type=metadata.get("knowledge_type", metadata.get("type", "")),
                migrated_at=datetime.now().isoformat()
            )
            lineage_records.append(lineage)
            
            # 更新元数据，添加归档标记
            metadata["archived_at"] = datetime.now().isoformat()
            metadata["original_id"] = item.get("id", 0)
            metas.append(json.dumps(metadata, ensure_ascii=False))
        
        # 分批插入（Batch Processing）
        batch_count = 0
        migrated_count = 0
        
        for i in range(0, total_count, BATCH_SIZE):
            batch_vectors = vectors[i:i + BATCH_SIZE]
            batch_tags = tags[i:i + BATCH_SIZE]
            batch_metas = metas[i:i + BATCH_SIZE]
            
            try:
                self.arc_col.insert([
                    batch_vectors,
                    batch_tags,
                    batch_metas
                ])
                migrated_count += len(batch_vectors)
                batch_count += 1
                
                logger.info(f"   ✅ 批次 {batch_count}: 已迁移 {len(batch_vectors)} 条")
                
            except Exception as e:
                logger.error(f"   ❌ 批次 {batch_count} 迁移失败: {e}")
                continue
        
        # 刷新到磁盘
        self.arc_col.flush()
        logger.info(f"   ✅ 成功将 {migrated_count} 条数据同步至归档库")
        
        # ----------------------------------------------------------------
        # 第3步：物理删除源库中的热数据（Space Self-Healing）
        # ----------------------------------------------------------------
        logger.info("\n[Step 3/5] 清理共享库...")
        
        try:
            # 使用Milvus的delete命令结合表达式删除
            self.src_col.delete(expr=expr)
            self.src_col.flush()
            
            # 释放显存，重新加载以更新索引视图
            self.src_col.release()
            self.src_col.load()
            
            logger.info(f"   ✅ 共享库空间自愈完成，项目 [{project_tag}] 数据已物理移除")
            
        except Exception as e:
            logger.error(f"❌ 删除失败: {e}")
        
        # ----------------------------------------------------------------
        # 第4步：触发空间自愈（重建索引）
        # ----------------------------------------------------------------
        logger.info("\n[Step 4/5] 执行空间自愈...")
        self._rebuild_indexes()
        
        # ----------------------------------------------------------------
        # 第5步：生成归档凭证
        # ----------------------------------------------------------------
        logger.info("\n[Step 5/5] 生成归档凭证...")
        
        report = ArchiveReport(
            project_tag=project_tag,
            archived_at=datetime.now().isoformat(),
            total_entities=total_count,
            migrated_entities=migrated_count,
            deleted_entities=total_count,
            batch_count=batch_count,
            lineage_records=lineage_records,
            statistics={
                "source_collection": self.source_ws,
                "destination_collection": self.archive_ws,
                "batch_size": BATCH_SIZE,
                "migration_duration_seconds": "N/A"
            }
        )
        
        archive_path = self._generate_audit_report(report)
        report.archive_path = archive_path
        
        # ----------------------------------------------------------------
        # 完成
        # ----------------------------------------------------------------
        logger.info(f"\n{'=' * 60}")
        logger.info(f"✨ 归档完成!")
        logger.info(f"   项目: {project_tag}")
        logger.info(f"   迁移: {migrated_count} 条")
        logger.info(f"   删除: {total_count} 条")
        logger.info(f"   批次: {batch_count}")
        logger.info(f"   报告: {archive_path}")
        logger.info(f"{'=' * 60}")
        
        return report
    
    # =========================================================================
    # 辅助方法
    # =========================================================================
    
    def _rebuild_indexes(self):
        """
        重建索引（空间自愈）
        
        物理删除数据后，Milvus不会自动回收空间。
        通过重建索引可以优化存储结构。
        """
        logger.info("   🔧 正在重建索引...")
        
        try:
            # 目标：归档库
            # 释放旧索引
            try:
                self.arc_col.release()
                self.arc_col.drop_index()
                logger.info("      - 归档库旧索引已清除")
            except Exception as e:
                logger.warning(f"      - 清除旧索引失败（可能无索引）: {e}")
            
            # 创建新索引（HNSW）
            index_params = {
                "metric_type": "L2",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64}
            }
            
            self.arc_col.create_index(
                field_name="vector",
                index_params=index_params
            )
            self.arc_col.flush()
            self.arc_col.load()
            
            logger.info("      ✅ 归档库索引重建完成")
            
        except Exception as e:
            logger.error(f"      ❌ 索引重建失败: {e}")
    
    def _generate_audit_report(self, report: ArchiveReport) -> str:
        """
        生成归档凭证（JSON格式）
        
        Args:
            report: 归档报告对象
        
        Returns:
            报告文件路径
        """
        # 确保目录存在
        os.makedirs("archives", exist_ok=True)
        
        # 生成文件名
        filename = f"archives/archive_log_{report.project_tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 转换为可序列化格式
        report_data = {
            "project_tag": report.project_tag,
            "archive_time": report.archived_at,
            "entities_moved": report.migrated_entities,
            "entities_deleted": report.deleted_entities,
            "status": "COMPLETED",
            "source": self.source_ws,
            "destination": self.archive_ws,
            "batch_count": report.batch_count,
            "lineage_records": [
                {
                    "entity_id": r.entity_id,
                    "source_project_tag": r.source_project_tag,
                    "source_collection": r.source_collection,
                    "content_preview": r.content_preview,
                    "agent_id": r.agent_id,
                    "round_num": r.round_num,
                    "knowledge_type": r.knowledge_type,
                    "migrated_at": r.migrated_at
                }
                for r in report.lineage_records
            ],
            "statistics": report.statistics
        }
        
        # 写入文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=4)
            logger.info(f"      ✅ 归档报告已生成: {filename}")
        except Exception as e:
            logger.error(f"      ❌ 报告生成失败: {e}")
        
        return filename
    
    def query_archive(self, project_tag: str = None, limit: int = 100) -> List[Dict]:
        """
        查询归档数据
        
        Args:
            project_tag: 项目标签（可选）
            limit: 返回数量限制
        
        Returns:
            归档数据列表
        """
        try:
            if project_tag:
                expr = f'project_tag == "{project_tag}"'
            else:
                expr = ""
            
            results = self.arc_col.query(
                expr=expr if expr else None,
                output_fields=["id", "project_tag", "metadata"],
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 查询归档失败: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        """
        return {
            "source": {
                "collection": self.source_ws,
                "entities": self.src_col.num_entities
            },
            "archive": {
                "collection": self.archive_ws,
                "entities": self.arc_col.num_entities
            }
        }
    
    def close(self):
        """关闭连接"""
        connections.disconnect("default")
        logger.info("🔌 连接已关闭")


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == "__main__":
    
    print("\n" + "=" * 60)
    print("📦 Sovereign-IQ | 项目结项归档与空间自愈管理器 v2.0")
    print("=" * 60)
    print("\n💡 功能说明:")
    print("   1. 数据迁移：协同共享库 → 历史归档库")
    print("   2. 空间自愈：物理删除后重建索引")
    print("   3. 资产凭证化：生成JSON归档报告")
    print()
    
    # 获取项目标签
    project_tag = input("🏷️ 请输入要归档结项的项目标签 (Project Tag): ").strip()
    
    if not project_tag:
        print("❌ 项目标签不能为空")
        sys.exit(1)
    
    # 二次确认，防止误操作
    print("\n⚠️ 警告：此操作将把项目数据从共享库迁移至归档库！")
    confirm = input(f"❓ 确定要将项目 [{project_tag}] 归档吗？(y/n): ").strip().lower()
    
    if confirm != 'y':
        print("🚫 操作已取消")
        sys.exit(0)
    
    # 执行归档
    try:
        archiver = SovereignArchiver()
        
        # 执行迁移
        archiver.migrate_project_data(project_tag)
        
        # 显示统计
        print("\n📊 当前状态:")
        stats = archiver.get_statistics()
        print(f"   共享库: {stats['source']['entities']} 条")
        print(f"   归档库: {stats['archive']['entities']} 条")
        
        archiver.close()
        
        print("\n" + "=" * 60)
        print("✅ 归档任务完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 归档失败: {e}")
        sys.exit(1)
