#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sovereign-IQ Evolution Recorder (V2.0 - Production Grade)
---------------------------------------------------------
功能：
1. 过程存证：实时记录投决会讨论细节，存入共享工作区（Shared WS）。
2. 逻辑进化：识别高价值观点（第三轮），将其"升维"回传至专家的私有知识库（Private WS）。
3. 去重机制：避免相同的经验反复回传私有库。
4. 知识分流：实现"项目事实"与"通用逻辑"的差异化存储。

设计模式：
- Observer Pattern：监听讨论流。
- Strategy Pattern：根据发言者动态切换存储目标。
- Deduplication：基于内容Hash的去重机制。
"""

import os
import sys
import json
import time
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 核心依赖
from openai import OpenAI
from pymilvus import connections, Collection, utility

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("EvolutionRecorder")

# ============================================================================
# 常量配置
# ============================================================================

SHARED_COLLECTION = "ic_collaboration_shared_ws"  # 协同共享库
PRIVATE_COLLECTIONS = {
    "ic_master_coordinator": "ic_master_coordinator_ws",
    "ic_chairman": "ic_chairman_ws",
    "ic_finance_auditor": "ic_finance_auditor_ws",
    "ic_legal_scanner": "ic_legal_scanner_ws",
    "ic_risk_controller": "ic_risk_controller_ws",
    "ic_sector_expert": "ic_sector_expert_ws",
    "ic_strategist": "ic_strategist_ws",
}

EMBEDDING_API = "http://127.0.0.1:11434/v1"
EMBEDDING_MODEL = "qwen3-vl-embedding"
VECTOR_DIM = 1024

# 去重缓存文件
DEDUP_CACHE = ".evolution_dedup_cache.json"


# ============================================================================
# 主类
# ============================================================================

class EvolutionRecorder:
    """
    Sovereign-IQ 决策进化记录器
    
    核心职责：
    1. 过程存证：所有观点存入共享库
    2. 逻辑进化：高价值观点回传私有库
    3. 去重机制：避免重复回传
    """
    
    def __init__(self, base_url: str = EMBEDDING_API):
        self.base_url = base_url
        self.client = OpenAI(api_key="EMPTY", base_url=base_url)
        
        # 初始化连接
        self._init_connections()
        
        # 加载去重缓存
        self.dedup_cache = self._load_dedup_cache()
        
        logger.info("✅ EvolutionRecorder 初始化完成")
    
    def _init_connections(self):
        """初始化Milvus连接"""
        try:
            connections.connect("default", host="localhost", port="19530")
            
            # 加载共享库
            if utility.has_collection(SHARED_COLLECTION):
                self.shared_col = Collection(SHARED_COLLECTION)
                self.shared_col.load()
                logger.info(f"✅ 已挂载共享库: {SHARED_COLLECTION}")
            else:
                raise RuntimeError(f"共享库 {SHARED_COLLECTION} 不存在")
            
            # 预加载所有私有库连接
            self.private_cols = {}
            for agent_id, coll_name in PRIVATE_COLLECTIONS.items():
                if utility.has_collection(coll_name):
                    col = Collection(coll_name)
                    col.load()
                    self.private_cols[agent_id] = col
                    logger.info(f"✅ 已挂载私有库: {coll_name}")
            
        except Exception as e:
            logger.error(f"❌ 连接失败: {e}")
            raise
    
    # =========================================================================
    # 向量化接口
    # =========================================================================
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        调用Qwen3-VL-Embedding生成向量
        
        Args:
            text: 文本内容
            
        Returns:
            2048维向量
        """
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[{"type": "text", "text": text}],
                timeout=60.0
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ 向量化失败: {e}")
            return []
    
    # =========================================================================
    # 去重机制
    # =========================================================================
    
    def _load_dedup_cache(self) -> Dict[str, str]:
        """加载去重缓存"""
        if os.path.exists(DEDUP_CACHE):
            try:
                with open(DEDUP_CACHE, 'r') as f:
                    cache = json.load(f)
                    logger.info(f"📋 已加载去重缓存: {len(cache)} 条记录")
                    return cache
            except Exception as e:
                logger.warning(f"⚠️ 加载去重缓存失败: {e}")
        return {}
    
    def _save_dedup_cache(self):
        """保存去重缓存"""
        try:
            with open(DEDUP_CACHE, 'w') as f:
                json.dump(self.dedup_cache, f)
        except Exception as e:
            logger.error(f"❌ 保存去重缓存失败: {e}")
    
    def _compute_content_hash(self, content: str, agent_id: str) -> str:
        """
        计算内容Hash（用于去重）
        
        策略：以内容+agent_id的组合计算Hash
        这样同一agent的相似内容会被识别
        """
        # 标准化内容：去除多余空格、换行
        normalized = " ".join(content.split())
        hash_input = f"{agent_id}:{normalized}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _is_duplicate(self, content_hash: str) -> bool:
        """检查是否重复"""
        return content_hash in self.dedup_cache
    
    def _mark_as_recorded(self, content_hash: str, metadata: Dict):
        """标记为已记录"""
        self.dedup_cache[content_hash] = {
            "recorded_at": datetime.now().isoformat(),
            "metadata": metadata
        }
        self._save_dedup_cache()
    
    # =========================================================================
    # 核心接口：记录发言
    # =========================================================================
    
    def record(
        self,
        agent_id: str,
        project_tag: str,
        content: str,
        round_num: int,
        viewpoint_type: str = "opinion",
        reference_ids: List[str] = None,
        is_methodology: bool = False
    ):
        """
        [核心接口] 记录一条发言
        
        Args:
            agent_id: 发言者ID (如 'ic_finance_auditor')
            project_tag: 项目标签 (如 'YUSHU_2026')
            content: 发言原始文本
            round_num: 第几轮 (1/2/3)
            viewpoint_type: 观点类型 ('opinion'/'red_blue')
            reference_ids: 引用的观点ID列表
            is_methodology: 是否具有方法论价值（第三轮自动为True）
        """
        # 1. 生成向量
        vector = self._get_embedding(content)
        if not vector:
            logger.error("❌ 向量生成失败，跳过存证")
            return None
        
        # 2. 生成观点ID
        viewpoint_id = str(uuid.uuid4())[:8]
        
        # 3. 构造元数据
        shared_meta = {
            "viewpoint_id": viewpoint_id,
            "agent_id": agent_id,
            "project_tag": project_tag,
            "round": round_num,
            "viewpoint_type": viewpoint_type,
            "content": content[:1000],  # 完整内容存预览
            "full_content": content,     # 完整内容
            "reference_viewpoints": reference_ids or [],
            "is_methodology": is_methodology,
            "timestamp": datetime.now().isoformat(),
            "source": "evolution_recorder"
        }
        
        # 4. 存入共享库（所有观点都存）
        try:
            self.shared_col.insert([
                [vector],
                [project_tag],
                [json.dumps(shared_meta, ensure_ascii=False)]
            ])
            self.shared_col.flush()
            logger.info(f"🎙️ [共享库] {agent_id} 第{round_num}轮发言已存证 (ID: {viewpoint_id})")
        except Exception as e:
            logger.error(f"❌ 共享库存证失败: {e}")
            return None
        
        # 5. 判断是否需要回传私有库
        if is_methodology:
            self._crystallize_to_private(
                agent_id=agent_id,
                project_tag=project_tag,
                content=content,
                vector=vector,
                round_num=round_num,
                viewpoint_id=viewpoint_id
            )
        
        return viewpoint_id
    
    # =========================================================================
    # 逻辑回传（仅方法论）
    # =========================================================================
    
    def _crystallize_to_private(
        self,
        agent_id: str,
        project_tag: str,
        content: str,
        vector: List[float],
        round_num: int,
        viewpoint_id: str
    ):
        """
        将高价值观点回传至专家私有库
        
        规则：
        1. 检查去重缓存
        2. 未重复 → 写入私有库 + 更新缓存
        3. 已重复 → 跳过
        """
        # 计算内容Hash
        content_hash = self._compute_content_hash(content, agent_id)
        
        # 检查是否重复
        if self._is_duplicate(content_hash):
            logger.info(f"⏭️ [去重] {agent_id} 的方法论已存在，跳过回传")
            return
        
        # 获取目标私有库
        target_ws = PRIVATE_COLLECTIONS.get(agent_id)
        if not target_ws:
            logger.warning(f"⚠️ 未找到 {agent_id} 的私有库")
            return
        
        try:
            private_col = Collection(target_ws)
            
            # 构造私有库元数据（更强调方法论属性）
            private_meta = {
                "knowledge_type": "methodology",        # 知识类型：方法论
                "source_project": project_tag,          # 来源项目
                "source_viewpoint_id": viewpoint_id,   # 来源观点ID
                "round": round_num,                     # 来源轮次
                "agent_id": agent_id,                   # 来源Agent
                "crystallized_at": datetime.now().isoformat(),  # 结晶时间
                "content": content,                     # 完整内容
                "content_hash": content_hash            # 用于去重
            }
            
            private_col.insert([
                [vector],
                [project_tag],
                [json.dumps(private_meta, ensure_ascii=False)]
            ])
            private_col.flush()
            
            # 更新去重缓存
            self._mark_as_recorded(content_hash, {
                "agent_id": agent_id,
                "project_tag": project_tag,
                "viewpoint_id": viewpoint_id
            })
            
            logger.info(f"✨ [私有库] 方法论已回传至 {target_ws}")
            
        except Exception as e:
            logger.error(f"❌ 私有库回传失败: {e}")
    
    # =========================================================================
    # 便捷接口
    # =========================================================================
    
    def record_round1(self, agent_id: str, project_tag: str, content: str) -> str:
        """
        第一轮观点：看完底稿后的初次观点
        
        不自动标记为方法论
        """
        return self.record(
            agent_id=agent_id,
            project_tag=project_tag,
            content=content,
            round_num=1,
            viewpoint_type="opinion",
            is_methodology=False
        )
    
    def record_round2(
        self,
        agent_id: str,
        project_tag: str,
        content: str,
        reference_ids: List[str] = None
    ) -> str:
        """
        第二轮观点：看完其他观点后的完善观点
        
        自动标记为方法论，触发私有库回传
        """
        return self.record(
            agent_id=agent_id,
            project_tag=project_tag,
            content=content,
            round_num=2,
            viewpoint_type="opinion",
            reference_ids=reference_ids,
            is_methodology=True  # 第二轮也需要进入私有库
        )
    
    def record_round3(
        self,
        agent_id: str,
        project_tag: str,
        content: str,
        reference_ids: List[str] = None
    ) -> str:
        """
        第三轮观点：红蓝对抗后的精华观点
        
        自动标记为方法论，触发私有库回传
        """
        return self.record(
            agent_id=agent_id,
            project_tag=project_tag,
            content=content,
            round_num=3,
            viewpoint_type="red_blue",
            reference_ids=reference_ids,
            is_methodology=True  # 第三轮自动为方法论
        )
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            "shared_col_entities": self.shared_col.num_entities,
            "dedup_cache_size": len(self.dedup_cache),
            "private_col_entities": {}
        }
        
        for agent_id, col in self.private_cols.items():
            stats["private_col_entities"][agent_id] = col.num_entities
        
        return stats
    
    def close(self):
        """关闭连接"""
        connections.disconnect("default")
        logger.info("🔌 连接已关闭")


# ============================================================================
# 测试/演示入口
# ============================================================================

def main():
    """演示EvolutionRecorder的使用"""
    
    print("\n" + "=" * 60)
    print("✨ Sovereign-IQ | 决策进化记录器 v2.0")
    print("=" * 60)
    print("\n💡 使用说明:")
    print("   1. 本脚本用于记录Agent在投决会中的发言")
    print("   2. 所有发言都会存入共享库")
    print("   3. 第三轮发言会自动标记为方法论，回传私有库")
    print("   4. 相同内容不会重复回传私有库")
    print()
    
    # 输入项目信息
    project_tag = input("🏷️ 请输入项目标签 (如 YUSHU_2026): ").strip()
    
    if not project_tag:
        print("❌ project_tag 不能为空")
        return
    
    print("\n" + "-" * 60)
    print("📝 演示：模拟三轮观点记录")
    print("   第二轮、第三轮都会回传私有库")
    print("-" * 60)
    
    try:
        recorder = EvolutionRecorder()
        
        # 模拟Agent ID
        agent_id = "ic_finance_auditor"
        
        # ----------------------------------------------------------------
        # 第一轮：看完底稿后的观点
        # ----------------------------------------------------------------
        print("\n📤 第一轮发言（存入共享库，不回传私有库）")
        content_r1 = (
            "根据底稿分析，该公司2024年营收3.92亿元，"
            "但现金流为负且研发投入占比高达65%。"
            "建议财务审计重点关注研发费用的资本化处理。"
        )
        print(f"   Agent: {agent_id}")
        print(f"   内容: {content_r1[:50]}...")
        
        vid_r1 = recorder.record_round1(agent_id, project_tag, content_r1)
        print(f"   ✅ 已存证，观点ID: {vid_r1}")
        
        # ----------------------------------------------------------------
        # 第二轮：看完其他观点后的完善
        # ----------------------------------------------------------------
        print("\n📤 第二轮发言（存入共享库 + 回传私有库）")
        content_r2 = (
            "结合法律专家的意见，补充："
            "该公司的研发费用资本化政策符合会计准则，"
            "但存在将经常性支出资本化的风险，需要在审计报告中披露。"
        )
        print(f"   Agent: {agent_id}")
        print(f"   内容: {content_r2[:50]}...")
        
        vid_r2 = recorder.record_round2(agent_id, project_tag, content_r2, [vid_r1])
        print(f"   ✅ 已存证，观点ID: {vid_r2}")
        print(f"   ✨ 方法论已回传至 {agent_id} 私有库")
        
        # ----------------------------------------------------------------
        # 第三轮：红蓝对抗精华（自动触发私有库回传）
        # ----------------------------------------------------------------
        print("\n📤 第三轮发言（存入共享库 + 回传私有库）")
        content_r3 = (
            "综合三轮讨论，我总结出一个通用方法论："
            "对于研发驱动型初创公司，评估其价值时应采用'市研率'指标，"
            "即市值/研发投入，而不是传统PE估值。"
            "这个方法论可复用到所有同类项目。"
        )
        print(f"   Agent: {agent_id}")
        print(f"   内容: {content_r3[:50]}...")
        
        vid_r3 = recorder.record_round3(agent_id, project_tag, content_r3, [vid_r1, vid_r2])
        print(f"   ✅ 已存证，观点ID: {vid_r3}")
        print(f"   ✨ 方法论已回传至 {agent_id} 私有库")
        
        # ----------------------------------------------------------------
        # 再次记录相同内容（测试去重）
        # ----------------------------------------------------------------
        print("\n📤 重复发言（测试去重机制）")
        print(f"   再次提交第三轮相同内容...")
        
        vid_r3_dup = recorder.record_round3(agent_id, project_tag, content_r3, [vid_r1, vid_r2])
        if vid_r3_dup is None:
            print(f"   ⏭️ 已去重，跳过回传（符合预期）")
        
        # ----------------------------------------------------------------
        # 显示统计
        # ----------------------------------------------------------------
        print("\n📊 统计信息:")
        stats = recorder.get_statistics()
        print(f"   共享库实体数: {stats['shared_col_entities']}")
        print(f"   去重缓存: {stats['dedup_cache_size']} 条")
        print(f"   私有库实体数:")
        for aid, count in stats["private_col_entities"].items():
            print(f"      {aid}: {count}")
        
        recorder.close()
        
        print("\n" + "=" * 60)
        print("✅ 演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()
