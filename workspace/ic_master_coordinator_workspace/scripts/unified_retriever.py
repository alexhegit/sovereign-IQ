#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sovereign-IQ Unified Retriever for Chairman (V2.0)
---------------------------------------------------------
功能：主席Agent的全知检索与投决报告生成
- 跨库联邦检索：穿透事实库、方法论库、归档库
- 证据链构建：将碎片信息还原为逻辑证据
- 投决报告生成：支撑主席输出高质量决策报告

设计亮点：
1. 复合检索(Hybrid Search)：Project Tag强过滤 + 向量相似度
2. 跨库联邦(Cross-Coll)：事实库+方法论库+归档库同步检索
3. 证据链重组：将碎片化结果还原为"证据链"
4. 报告自动生成：结构化输出投决所需的关键维度
"""

import os
import sys
import json
import time
import logging
from typing import List, Dict,Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# 核心依赖
# from openai import OpenAI
# from pymilvus import connections, Collection, utility

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# 常量配置
# ============================================================================

# Collection配置
COLLECTIONS = {
    "shared": "ic_collaboration_shared_ws",          # 协同共享库（项目事实+观点）
    "archive": "ic_archive_sop_ws",                  # 归档库（历史项目）
    "chairman": "ic_chairman_ws",                   # 主席私有库
    "finance": "ic_finance_auditor_ws",             # 财务专家私有库
    "legal": "ic_legal_scanner_ws",                 # 法律专家私有库
    "risk": "ic_risk_controller_ws",                 # 风控专家私有库
    "sector": "ic_sector_expert_ws",                # 行业专家私有库
    "strategist": "ic_strategist_ws",               # 战略专家私有库
    "coordinator": "ic_master_coordinator_ws",       # 秘书私有库
}

EMBEDDING_API = "http://127.0.0.1:11434/v1"
EMBEDDING_MODEL = "qwen3-embedding:4b"
VECTOR_DIM = 2048

# 主席检索专用Collection（全部）
CHAIRMAN_COLLECTIONS = ["shared", "archive", "chairman", "finance", "legal", "risk", "sector", "strategist", "coordinator"]

# ============================================================================
# 角色配置
# ============================================================================

# 投委会角色发言顺序（由秘书协调）
DEBATE_SEQUENCE = [
    {"agent_id": "ic_strategist", "role_name": "战略专家", "focus": "宏观战略、政策导向、资金流向、赛道配置"},
    {"agent_id": "ic_sector_expert", "role_name": "行业专家", "focus": "行业分析、市场规模、竞争格局、技术路线"},
    {"agent_id": "ic_finance_auditor", "role_name": "财务专家", "focus": "财务分析、估值模型、现金流、盈利模式"},
    {"agent_id": "ic_legal_scanner", "role_name": "法律专家", "focus": "法律合规、股权结构、监管合规、知识产权"},
    {"agent_id": "ic_risk_controller", "role_name": "风控专家", "focus": "风险评估、ESG、舆情、供应链、行业周期"},
    {"agent_id": "ic_chairman", "role_name": "主席", "focus": "综合各方意见，给出最终决策"},
]


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class SearchResult:
    """检索结果"""
    content: str
    source: str
    source_type: str       # shared/archive/private
    agent_id: str         # 来源Agent
    project_tag: str
    score: float          # 相似度分数
    metadata: Dict = field(default_factory=dict)
    knowledge_type: str = ""  # methodology/fact/discussion
    round: int = 0        # 观点轮次


@dataclass
class EvidenceChain:
    """证据链"""
    dimension: str         # 证据维度（财务/法律/风险等）
    evidence_type: str     # evidence_type: fact/methodology/lesson
    items: List[SearchResult] = field(default_factory=list)
    summary: str = ""      # 证据链摘要


@dataclass
class RoleViewpoint:
    """角色最终发言"""
    agent_id: str
    role_name: str
    focus: str
    round1_content: str = ""    # 第一轮观点
    round2_content: str = ""    # 第二轮观点
    round3_content: str = ""     # 第三轮观点
    final_summary: str = ""      # 最终总结
    key_evidence: List[str] = field(default_factory=list)  # 关键证据


@dataclass
class ICReport:
    """投决报告"""
    project_tag: str
    generated_at: str
    query_count: int       # 检索次数
    evidence_chains: List[EvidenceChain] = field(default_factory=list)
    role_viewpoints: List[RoleViewpoint] = field(default_factory=list)  # 各角色最终发言
    chairman_decision: str = ""   # 主席最终决策
    executive_summary: str = ""
    risk_summary: str = ""
    recommendation: str = ""


# ============================================================================
# 主类
# ============================================================================

class ChairmanRetriever:
    """
    Sovereign-IQ 主席检索器
    
    核心职责：
    1. 全知检索：穿透所有库，获取全局视角
    2. 证据链构建：从碎片化结果中提炼证据
    3. 报告生成：支撑主席输出高质量投决报告
    """
    
    def __init__(self, base_url: str = EMBEDDING_API):
        self.base_url = base_url
        self.client = OpenAI(api_key="EMPTY", base_url=base_url)
        
        # 初始化连接
        self._init_connections()
        
        logger.info("✅ ChairmanRetriever 初始化完成")
    
    def _init_connections(self):
        """初始化Milvus连接"""
        try:
            connections.connect("default", host="localhost", port="19530")
            
            # 加载所有Collection
            self.collections = {}
            for name, coll_name in COLLECTIONS.items():
                if utility.has_collection(coll_name):
                    col = Collection(coll_name)
                    col.load()
                    self.collections[name] = col
                    logger.info(f"✅ 已挂载: {coll_name} ({col.num_entities} 条)")
            
            # 加载专家Collection映射
            self.expert_collections = {
                "finance": "ic_finance_auditor_ws",
                "legal": "ic_legal_scanner_ws",
                "risk": "ic_risk_controller_ws",
                "sector": "ic_sector_expert_ws",
                "strategist": "ic_strategist_ws",
                "chairman": "ic_chairman_ws",
                "coordinator": "ic_master_coordinator_ws"
            }
            
        except Exception as e:
            logger.error(f"❌ 连接失败: {e}")
            raise
    
    # =========================================================================
    # 向量化接口
    # =========================================================================
    
    def _get_embedding(self, text: str) -> List[float]:
        """调用向量化接口"""
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
    # 核心检索
    # =========================================================================
    
    def _search_single(
        self,
        collection_name: str,
        query_vector: List[float],
        project_tag: str = None,
        top_k: int = 5,
        ef: int = 128
    ) -> List[SearchResult]:
        """
        在单个Collection中检索
        """
        if collection_name not in self.collections:
            return []
        
        col = self.collections[collection_name]
        results = []
        
        try:
            # 构建过滤表达式
            expr = f'project_tag == "{project_tag}"' if project_tag else None
            
            # HNSW检索参数
            search_params = {
                "metric_type": "L2",
                "params": {"ef": ef}
            }
            
            hits = col.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["metadata", "project_tag"]
            )
            
            for hit in hits[0]:
                try:
                    metadata = self._parse_metadata(hit.entity.get("metadata", "{}"))
                    
                    result = SearchResult(
                        content=metadata.get("content", metadata.get("content_preview", "")),
                        source=collection_name,
                        source_type=self._get_source_type(collection_name),
                        agent_id=metadata.get("agent_id", metadata.get("knowledge_type", "")),
                        project_tag=hit.entity.get("project_tag", ""),
                        score=1.0 / (1.0 + hit.distance),  # 转换distance为score
                        metadata=metadata,
                        knowledge_type=metadata.get("knowledge_type", metadata.get("type", "")),
                        round=metadata.get("round", 0)
                    )
                    results.append(result)
                except Exception as e:
                    logger.warning(f"⚠️ 解析结果失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ {collection_name} 检索失败: {e}")
        
        return results
    
    def _parse_metadata(self, metadata_str: str) -> Dict:
        """解析元数据"""
        if isinstance(metadata_str, dict):
            return metadata_str
        try:
            return json.loads(metadata_str) if metadata_str else {}
        except:
            return {}
    
    def _get_source_type(self, coll_name: str) -> str:
        """判断来源类型"""
        if coll_name == "shared":
            return "shared"
        elif coll_name == "archive":
            return "archive"
        else:
            return "private"
    
    # =========================================================================
    # 联邦检索（全库穿透）
    # =========================================================================
    
    def search_all(
        self,
        query: str,
        project_tag: str = None,
        top_k: int = 5,
        include_experts: bool = True
    ) -> List[SearchResult]:
        """
        [核心接口] 全库穿透检索
        
        Args:
            query: 查询文本
            project_tag: 项目标签（可选）
            top_k: 每库返回数量
            include_experts: 是否包含专家私有库
        """
        start_time = time.time()
        
        # 向量化
        query_vector = self._get_embedding(query)
        if not query_vector:
            return []
        
        logger.info(f"\n🔍 全库穿透检索: {query[:50]}...")
        if project_tag:
            logger.info(f"   项目: {project_tag}")
        
        all_results = []
        
        # 确定检索范围
        collections_to_search = ["shared", "archive"]
        if include_experts:
            collections_to_search.extend(list(self.expert_collections.keys()))
        
        # 并发检索
        for coll_name in collections_to_search:
            results = self._search_single(coll_name, query_vector, project_tag, top_k)
            if results:
                logger.info(f"   ✅ {coll_name}: {len(results)} 条")
                all_results.extend(results)
        
        # 排序去重
        aggregated = self._aggregate_results(all_results, top_k * 3)
        
        elapsed = time.time() - start_time
        logger.info(f"✨ 检索完成: {len(aggregated)} 条结果 ({elapsed*1000:.0f}ms)")
        
        return aggregated
    
    def _aggregate_results(self, results: List[SearchResult], limit: int) -> List[SearchResult]:
        """聚合结果并去重"""
        if not results:
            return []
        
        # 按score降序
        results.sort(key=lambda x: x.score, reverse=True)
        
        # 去重
        seen = set()
        deduplicated = []
        for r in results:
            key = hash(r.content[:100])
            if key not in seen:
                seen.add(key)
                deduplicated.append(r)
        
        return deduplicated[:limit]
    
    # =========================================================================
    # 证据链构建
    # =========================================================================
    
    def build_evidence_chains(
        self,
        results: List[SearchResult]
    ) -> List[EvidenceChain]:
        """
        构建证据链
        
        按维度分组：
        - 财务证据
        - 法律证据
        - 风险证据
        - 行业证据
        - 战略证据
        """
        # 定义维度映射
        dimension_mapping = {
            "finance": "财务",
            "legal": "法律",
            "risk": "风险",
            "sector": "行业",
            "strategist": "战略",
            "shared": "项目事实",
            "archive": "历史经验"
        }
        
        # 按来源分组
        chains_map = {}
        
        for r in results:
            # 确定维度
            if r.source in ["shared", "archive"]:
                dimension = dimension_mapping.get(r.source, r.source)
                evidence_type = "project_fact" if r.source == "shared" else "historical_lesson"
            else:
                dimension = dimension_mapping.get(r.source, "其他")
                evidence_type = "methodology" if r.knowledge_type == "methodology" else "discussion"
            
            if dimension not in chains_map:
                chains_map[dimension] = EvidenceChain(
                    dimension=dimension,
                    evidence_type=evidence_type,
                    items=[],
                    summary=""
                )
            
            chains_map[dimension].items.append(r)
        
        # 生成摘要
        for chain in chains_map.values():
            chain.summary = self._generate_chain_summary(chain)
        
        return list(chains_map.values())
    
    def _generate_chain_summary(self, chain: EvidenceChain) -> str:
        """生成证据链摘要"""
        if not chain.items:
            return ""
        
        summaries = []
        
        # 按轮次/类型排序
        items_by_type = {}
        for item in chain.items:
            key = f"轮次{item.round}" if item.round > 0 else "事实"
            if key not in items_by_type:
                items_by_type[key] = []
            items_by_type[key].append(item)
        
        for key, items in items_by_type.items():
            top_item = max(items, key=lambda x: x.score)
            preview = top_item.content[:100]
            summaries.append(f"{key}: {preview}...")
        
        return "\n".join(summaries)
    
    # =========================================================================
    # 投决报告生成
    # =========================================================================
    
    def generate_ic_report(
        self,
        project_tag: str,
        queries: Dict[str, str] = None
    ) -> ICReport:
        """
        [核心接口] 生成投决报告
        
        Args:
            project_tag: 项目标签
            queries: 多维度查询字典（可选，不传则自动生成）
        
        Returns:
            ICReport: 结构化投决报告
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"📊 正在生成投决报告: {project_tag}")
        logger.info(f"{'=' * 60}")
        
        # 默认查询
        if queries is None:
            queries = {
                "executive": "项目概述、核心亮点",
                "financial": "财务状况、估值分析",
                "legal": "法律合规、股权结构",
                "risk": "主要风险点",
                "industry": "行业分析",
                "strategy": "战略建议"
            }
        
        report = ICReport(
            project_tag=project_tag,
            generated_at=datetime.now().isoformat(),
            query_count=len(queries),
            evidence_chains=[],
            role_viewpoints=[]
        )
        
        all_results = []
        
        # ----------------------------------------------------------------
        # 第一步：按角色检索三轮观点
        # ----------------------------------------------------------------
        logger.info(f"\n📋 检索各角色最终发言...")
        
        for role in DEBATE_SEQUENCE:
            agent_id = role["agent_id"]
            role_name = role["role_name"]
            focus = role["focus"]
            
            logger.info(f"\n📂 [{role_name}] {focus}...")
            
            # 检索该角色的所有观点
            viewpoint = self._retrieve_role_viewpoint(
                agent_id=agent_id,
                role_name=role_name,
                focus=focus,
                project_tag=project_tag
            )
            
            report.role_viewpoints.append(viewpoint)
        
        # ----------------------------------------------------------------
        # 第二步：综合检索构建证据链
        # ----------------------------------------------------------------
        logger.info(f"\n📊 构建综合证据链...")
        
        for dimension, query in queries.items():
            results = self.search_all(query, project_tag, top_k=5)
            all_results.extend(results)
        
        report.evidence_chains = self.build_evidence_chains(all_results)
        
        # ----------------------------------------------------------------
        # 第三步：生成摘要和建议
        # ----------------------------------------------------------------
        report.executive_summary = self._generate_executive_summary(report.evidence_chains)
        report.risk_summary = self._generate_risk_summary(report.evidence_chains)
        report.chairman_decision = self._generate_chairman_decision(report.role_viewpoints)
        report.recommendation = self._generate_recommendation(report.role_viewpoints)
        
        logger.info(f"\n✨ 报告生成完成")
        
        return report
    
    def _retrieve_role_viewpoint(
        self,
        agent_id: str,
        role_name: str,
        focus: str,
        project_tag: str
    ) -> RoleViewpoint:
        """
        检索单个角色的最终发言概况
        """
        viewpoint = RoleViewpoint(
            agent_id=agent_id,
            role_name=role_name,
            focus=focus
        )
        
        try:
            # 检索该角色在共享库中的所有观点
            if "shared" in self.collections:
                col = self.collections["shared"]
                
                # 构建查询向量
                query_text = f"{role_name} {focus}"
                query_vector = self._get_embedding(query_text)
                
                if query_vector:
                    # 检索观点（按agent_id过滤）
                    search_params = {"metric_type": "L2", "params": {"ef": 128}}
                    
                    hits = col.search(
                        data=[query_vector],
                        anns_field="vector",
                        param=search_params,
                        limit=20,  # 检索多条
                        expr=f'project_tag == "{project_tag}"',
                        output_fields=["metadata", "project_tag"]
                    )
                    
                    # 按轮次整理观点
                    round1_items = []
                    round2_items = []
                    round3_items = []
                    
                    for hit in hits[0]:
                        try:
                            metadata = self._parse_metadata(hit.entity.get("metadata", "{}"))
                            
                            if metadata.get("agent_id") == agent_id:
                                content = metadata.get("content", metadata.get("content_preview", ""))
                                round_num = metadata.get("round", 0)
                                
                                if round_num == 1:
                                    round1_items.append(content)
                                elif round_num == 2:
                                    round2_items.append(content)
                                elif round_num == 3:
                                    round3_items.append(content)
                        except:
                            continue
                    
                    # 取最新的一条作为最终发言
                    viewpoint.round1_content = round1_items[0] if round1_items else ""
                    viewpoint.round2_content = round2_items[0] if round2_items else ""
                    viewpoint.round3_content = round3_items[0] if round3_items else ""
                    
                    # 生成最终总结（取最高分的观点）
                    all_items = round3_items or round2_items or round1_items
                    viewpoint.final_summary = all_items[0] if all_items else ""
                    
                    # 提取关键证据
                    viewpoint.key_evidence = all_items[:3] if all_items else []
                    
                    logger.info(f"   ✅ {role_name}: R1={len(round1_items)}, R2={len(round2_items)}, R3={len(round3_items)}")
        
        except Exception as e:
            logger.warning(f"⚠️ 检索 {role_name} 观点失败: {e}")
        
        return viewpoint
    
    def _generate_executive_summary(self, chains: List[EvidenceChain]) -> str:
        """生成执行摘要"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("📋 执行摘要")
        lines.append("=" * 70)
        
        for chain in chains:
            if chain.items:
                top_item = max(chain.items, key=lambda x: x.score)
                lines.append(f"\n【{chain.dimension}】")
                lines.append(f"  {top_item.content[:200]}...")
        
        return "\n".join(lines)
    
    def _generate_risk_summary(self, chains: List[EvidenceChain]) -> str:
        """生成风险摘要"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("⚠️ 风险摘要")
        lines.append("=" * 70)
        
        risk_chain = next((c for c in chains if c.dimension == "风险"), None)
        if risk_chain and risk_chain.items:
            for item in risk_chain.items[:3]:
                lines.append(f"\n• {item.content[:150]}...")
        else:
            lines.append("\n未发现重大风险信号")
        
        return "\n".join(lines)
    
    def _generate_recommendation(self, role_viewpoints: List[RoleViewpoint]) -> str:
        """生成投资建议"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("🎯 投决建议")
        lines.append("=" * 70)
        
        # 统计三轮发言情况
        r3_count = sum(1 for v in role_viewpoints if v.round3_content)
        r2_count = sum(1 for v in role_viewpoints if v.round2_content)
        r1_count = sum(1 for v in role_viewpoints if v.round1_content)
        
        if r3_count >= 4:
            lines.append("\n✅ 建议：可推进尽调")
            lines.append(f"   依据：{r3_count}位专家完成第三轮讨论，{r2_count}位完成第二轮")
        elif r2_count >= 3:
            lines.append("\n⚠️ 建议：需进一步验证")
            lines.append(f"   依据：{r2_count}位专家完成第二轮，需进入红蓝对抗")
        elif r1_count >= 2:
            lines.append("\n⚠️ 建议：需补充尽调")
            lines.append(f"   依据：仅{r1_count}位专家完成第一轮，需完善讨论")
        else:
            lines.append("\n❌ 建议：暂不推进")
            lines.append("   依据：讨论不充分，建议重新组织尽调")
        
        return "\n".join(lines)
    
    def _generate_chairman_decision(self, role_viewpoints: List[RoleViewpoint]) -> str:
        """生成主席最终决策"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("🏛️ 主席最终决策")
        lines.append("=" * 70)
        
        # 统计各角色发言
        lines.append("\n【各角色发言统计】")
        for v in role_viewpoints:
            rounds = []
            if v.round1_content:
                rounds.append("R1")
            if v.round2_content:
                rounds.append("R2")
            if v.round3_content:
                rounds.append("R3")
            
            rounds_str = "+".join(rounds) if rounds else "未发言"
            lines.append(f"  • {v.role_name}: {rounds_str}")
        
        # 综合意见摘要
        lines.append("\n【综合意见】")
        
        # 按顺序展示每轮讨论
        for round_num in [1, 2, 3]:
            round_key = f"round{round_num}_content"
            contents = [getattr(v, round_key) for v in role_viewpoints if getattr(v, round_key)]
            
            if contents:
                round_title = {1: "第一轮", 2: "第二轮", 3: "第三轮（红蓝对抗）"}
                lines.append(f"\n  {round_title[round_num]}发言：")
                for i, content in enumerate(contents[:2]):  # 最多显示2条
                    role_name = role_viewpoints[i].role_name
                    lines.append(f"    - {role_name}: {content[:80]}...")
        
        # 最终决策
        lines.append("\n" + "-" * 70)
        lines.append("【最终决策】")
        
        # 基于发言情况生成决策
        r3_count = sum(1 for v in role_viewpoints if v.round3_content)
        
        if r3_count >= 4:
            decision = "✅ 建议推进：经过充分讨论，建议进入下一阶段尽调"
        elif r3_count >= 2:
            decision = "⚠️ 有条件通过：需补充部分讨论后推进"
        else:
            decision = "❌ 暂不通过：需重新组织充分讨论"
        
        lines.append(f"\n  {decision}")
        lines.append(f"\n  主席签字: _____________  日期: {datetime.now().strftime('%Y-%m-%d')}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # 报告格式化
    # =========================================================================
    
    def format_report(self, report: ICReport) -> str:
        """格式化投决报告"""
        lines = []
        
        lines.append("\n" + "=" * 70)
        lines.append("🏛️ SIQ 投决报告")
        lines.append("=" * 70)
        lines.append(f"项目: {report.project_tag}")
        lines.append(f"生成时间: {report.generated_at}")
        
        # ----------------------------------------------------------------
        # 第一部分：各角色最终发言概况
        # ----------------------------------------------------------------
        lines.append("\n" + "=" * 70)
        lines.append("👥 各角色最终发言概况")
        lines.append("=" * 70)
        lines.append("\n发言顺序:")
        for i, role in enumerate(DEBATE_SEQUENCE, 1):
            lines.append(f"  {i}. {role['role_name']} - {role['focus']}")
        
        # 每轮发言详情
        for round_num in [1, 2, 3]:
            round_title = {1: "第一轮发言（看完底稿）", 2: "第二轮发言（看完其他观点）", 3: "第三轮发言（红蓝对抗）"}
            round_key = f"round{round_num}_content"
            
            lines.append(f"\n{'─' * 70}")
            lines.append(f"📤 {round_title[round_num]}")
            lines.append(f"{'─' * 70}")
            
            for viewpoint in report.role_viewpoints:
                content = getattr(viewpoint, round_key)
                if content:
                    lines.append(f"\n【{viewpoint.role_name}】")
                    lines.append(f"  {content[:150]}...")
        
        # ----------------------------------------------------------------
        # 第二部分：各角色最终总结
        # ----------------------------------------------------------------
        lines.append("\n" + "=" * 70)
        lines.append("📋 各角色最终总结")
        lines.append("=" * 70)
        
        for viewpoint in report.role_viewpoints:
            if viewpoint.final_summary:
                lines.append(f"\n【{viewpoint.role_name}】")
                lines.append(f"  {viewpoint.final_summary[:200]}...")
        
        # ----------------------------------------------------------------
        # 第三部分：主席最终决策
        # ----------------------------------------------------------------
        if report.chairman_decision:
            lines.append(report.chairman_decision)
        
        # ----------------------------------------------------------------
        # 第四部分：证据链详情
        # ----------------------------------------------------------------
        lines.append("\n" + "=" * 70)
        lines.append("📑 详细证据链")
        lines.append("=" * 70)
        
        for chain in report.evidence_chains:
            lines.append(f"\n【{chain.dimension}】({chain.evidence_type})")
            lines.append(f"证据数量: {len(chain.items)}")
            for item in chain.items[:3]:  # 每条链最多显示3条
                lines.append(f"  • [{item.source}] {item.content[:80]}...")
        
        lines.append("\n" + "=" * 70)
        lines.append(f"报告生成: ChairmanRetriever v2.0")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def close(self):
        """关闭连接"""
        connections.disconnect("default")
        logger.info("🔌 连接已关闭")


# ============================================================================
# 测试/演示入口
# ============================================================================

def main():
    """演示ChairmanRetriever的使用"""
    
    print("\n" + "=" * 70)
    print("🏛️ Sovereign-IQ | 主席全知检索与投决报告生成器 v2.0")
    print("=" * 70)
    
    project_tag = input("\n🏷️ 请输入项目标签 (如 YUSHU_2026): ").strip()
    
    if not project_tag:
        print("❌ 项目标签不能为空")
        return
    
    print("\n💡 请选择检索模式:")
    print("  [1] 快速检索 (共享库)")
    print("  [2] 全库检索 (含专家私有库)")
    print("  [3] 生成完整投决报告")
    
    mode = input("\n👉 请选择 (1/2/3): ").strip()
    
    try:
        retriever = ChairmanRetriever()
        
        if mode == "1":
            # 快速检索
            query = input("\n🔍 请输入查询: ").strip()
            if query:
                results = retriever.search_all(query, project_tag, top_k=10, include_experts=False)
                for r in results:
                    print(f"\n[{r.source}] {r.content[:100]}...")
        
        elif mode == "2":
            # 全库检索
            query = input("\n🔍 请输入查询: ").strip()
            if query:
                results = retriever.search_all(query, project_tag, top_k=10, include_experts=True)
                chains = retriever.build_evidence_chains(results)
                for chain in chains:
                    print(f"\n【{chain.dimension}】")
                    for r in chain.items[:2]:
                        print(f"  • {r.content[:80]}...")
        
        elif mode == "3":
            # 生成完整投决报告
            queries = {
                "executive": "项目概述、核心亮点、团队背景",
                "financial": "财务状况、估值分析、现金流",
                "legal": "法律合规、股权结构、诉讼风险",
                "risk": "主要风险点、风险缓释措施",
                "industry": "行业规模、竞争格局、市场趋势",
                "strategy": "战略协同、投资价值、退出路径"
            }
            
            print("\n📊 正在生成投决报告...")
            report = retriever.generate_ic_report(project_tag, queries)
            print(retriever.format_report(report))
        
        else:
            print("❌ 无效选择")
        
        retriever.close()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()
