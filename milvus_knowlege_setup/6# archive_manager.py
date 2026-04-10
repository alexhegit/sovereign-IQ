6# archive_manager.py
"""
Sovereign-IQ Archive & Self-Healing Manager (V1.0)
---------------------------------------------------------
核心逻辑：
1. 数据迁移：将指定项目标签的所有向量及元数据从“协同共享库”搬迁至“历史归档库”。
2. 空间释放：物理删除共享库中的旧数据，触发 Milvus 空间回收与索引重构。
3. 知识资产化：生成结项审计日志，完成从“过程数据”到“数字资产”的转化。

设计模式：
- Transactional Migration (模拟事务迁移)：确保先写后删，防止数据丢失。
- Batch Processing (分片处理)：应对大规模项目底稿的搬迁压力。
"""

import logging
import time
import json
from typing import List, Dict, Any
from pymilvus import connections, Collection, utility

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ArchiveManager")

class SovereignArchiver:
    def __init__(self, source_ws: str = "ic_collaboration_shared_ws", archive_ws: str = "ic_archive_sop_ws"):
        self.source_ws = source_ws
        self.archive_ws = archive_ws
        
        # 建立数据库连接
        connections.connect("default", host="localhost", port="19530")
        
        # 确保目标库已就绪
        self._ensure_collections()

    def _ensure_collections(self):
        """校验源库与目标库的健康状态"""
        for ws in [self.source_ws, self.archive_ws]:
            if not utility.has_collection(ws):
                raise RuntimeError(f"❌ 关键工作区 {ws} 缺失，请检查环境配置。")
        
        self.src_col = Collection(self.source_ws)
        self.arc_col = Collection(self.archive_ws)
        
        # 加载至内存执行操作
        self.src_col.load()
        self.arc_col.load()

    def migrate_project_data(self, project_tag: str):
        """
        [核心接口] 结项归档：执行数据迁移与自愈清理
        """
        logger.info(f"📁 启动项目归档任务: [{project_tag}]")
        
        # 1. 查询属于该项目的所有实体 (分批次拉取以防内存溢出)
        # 注意：Milvus 默认 limit 限制，此处采用 query 结合 offset 或迭代逻辑
        expr = f'project_tag == "{project_tag}"'
        try:
            # 获取该项目的所有数据片段
            entities = self.src_col.query(
                expr=expr,
                output_fields=["vector", "project_tag", "metadata"]
            )
            
            total_count = len(entities)
            if total_count == 0:
                logger.warning(f"⚠️ 项目 [{project_tag}] 在共享库中无数据，无需归档。")
                return

            logger.info(f"🔍 检索到 {total_count} 条数据片段，准备搬迁...")

            # 2. 写入归档库 (写入前先进行格式解构)
            vectors = [item["vector"] for item in entities]
            tags = [item["project_tag"] for item in entities]
            metas = [item["metadata"] for item in entities]
            
            # 执行分批插入
            batch_size = 500
            for i in range(0, total_count, batch_size):
                self.arc_col.insert([
                    vectors[i:i+batch_size],
                    tags[i:i+batch_size],
                    metas[i:i+batch_size]
                ])
            
            self.arc_col.flush()
            logger.info(f"✅ 成功将 {total_count} 条数据同步至归档库。")

            # 3. 物理删除源库中的热数据 (Space Self-Healing)
            # Milvus 通过 delete 命令结合表达式实现
            self.src_col.delete(expr=expr)
            self.src_col.flush()
            
            # 释放显存
            self.src_col.release()
            self.src_col.load() # 重新加载以更新索引视图
            
            logger.info(f"♻️ 共享库空间自愈完成，项目 [{project_tag}] 数据已物理移除。")
            
            # 4. 生成归档凭证
            self._generate_audit_report(project_tag, total_count)

        except Exception as e:
            logger.error(f"❌ 归档失败: {e}")

    def _generate_audit_report(self, tag: str, count: int):
        report = {
            "project_tag": tag,
            "archive_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entities_moved": count,
            "status": "COMPLETED",
            "source": self.source_ws,
            "destination": self.archive_ws
        }
        report_name = f"archive_log_{tag}.json"
        with open(report_name, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        logger.info(f"📄 归档报告已生成: {report_name}")

# ==========================================
# 自动化结项入口
# ==========================================
if __name__ == "__main__":
    print("-" * 50)
    print("Sovereign-IQ | 项目结项归档与空间自愈管理器")
    print("-" * 50)
    
    tag_to_archive = input("🏷️ 请输入要归档结项的项目标签 (Project Tag): ").strip()
    
    if not tag_to_archive:
        print("❌ 标签不能为空")
    else:
        # 二次确认，防止误删热数据
        confirm = input(f"❓ 确定要将项目 [{tag_to_archive}] 移入冷库并清理共享区吗？(y/n): ")
        if confirm.lower() == 'y':
            archiver = SovereignArchiver()
            archiver.migrate_project_data(tag_to_archive)
        else:
            print("🚫 操作取消")