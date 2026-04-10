#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent专用检索器 - Agent Retriever for SIQ (V2.0)
基于Agent角色定制查询，从Milvus检索相关专业片段

更新日志：
- V2.0: 从mock改为真正的Milvus向量检索
- 使用Ollama qwen3-vl-embedding (2048维)
- 应用agent_retrieval_config.json中的查询模板
"""

import json
import os
import sys
from typing import List, Dict, Optional, Any
from datetime import datetime

# 第三方库
from pymilvus import connections, Collection, utility
from openai import OpenAI

# 配置
SHARED_COLLECTION = "ic_collaboration_shared_ws"
VECTOR_DIM = 1024
EMBEDDING_API = "http://127.0.0.1:11434/v1"
EMBEDDING_MODEL = "qwen3-vl-embedding"


class AgentRetriever:
    """
    Agent专用检索器 - V2.0 真正Milvus向量检索
    
    功能：
    - 加载Agent定制查询配置
    - 构建专业检索查询（填充模板）
    - 生成查询向量（Ollama 2048维）
    - 从Milvus执行project_tag过滤+向量检索
    - 返回Top-20相关chunk，格式化为报告
    """
    
    def __init__(self, agent_id: str, project_tag: str):
        """
        初始化检索器
        
        Args:
            agent_id: Agent标识 (ic_strategist/ic_finance_auditor等)
            project_tag: 项目标签 (YUSHU_2026)
        """
        self.agent_id = agent_id
        self.project_tag = project_tag
        
        # 加载配置
        self.config = self._load_config()
        self.agent_config = self.config.get("agent_queries", {}).get(agent_id, {})
        self.retrieval_config = self.config.get("retrieval_config", {})
        self.chunk_config = self.config.get("chunk_config", {})
        
        # 初始化向量化客户端
        self.client = OpenAI(api_key="EMPTY", base_url=EMBEDDING_API)
        
        # 连接Milvus
        self._init_milvus()
        
        print(f"✅ Agent检索器初始化完成")
        print(f"   Agent: {agent_id} ({self.agent_config.get('role', 'Unknown')})")
        print(f"   项目: {project_tag}")
        print(f"   关注领域: {', '.join(self.agent_config.get('focus_areas', [])[:3])}")
    
    def _load_config(self) -> Dict:
        """加载检索配置"""
        config_path = os.path.expanduser(
            "~/.openclaw/workspace/ic_master_coordinator_workspace/config/agent_retrieval_config.json"
        )
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _init_milvus(self):
        """连接Milvus共享库"""
        try:
            connections.connect("default", host="localhost", port="19530")
            
            if not utility.has_collection(SHARED_COLLECTION):
                raise RuntimeError(f"共享库 {SHARED_COLLECTION} 不存在")
            
            self.collection = Collection(SHARED_COLLECTION)
            self.collection.load()
            print(f"✅ 已连接Milvus共享库: {SHARED_COLLECTION}")
            print(f"   当前实体数: {self.collection.num_entities}")
        except Exception as e:
            print(f"❌ Milvus连接失败: {e}")
            raise
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        调用Ollama生成查询向量（2048维）
        
        Args:
            texts: 查询文本列表
            
        Returns:
            向量列表，每个向量2048维
        """
        formatted = [{"type": "text", "text": t} for t in texts]
        
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=formatted,
                timeout=60.0
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            print(f"❌ 向量化失败: {e}")
            return []
    
    def _get_project_info(self) -> Dict:
        """从项目元数据获取信息"""
        meta_path = os.path.expanduser(
            f"~/.openclaw/workspace/projects/{self.project_tag}/project_meta.json"
        )
        
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {
            "company_name": self.project_tag,
            "industry": ""
        }
    
    def build_queries(self, custom_context: str = None) -> List[str]:
        """
        构建Agent专用检索查询列表
        
        根据agent_retrieval_config.json中的query_templates
        填充{company_name}和{industry}占位符
        
        Args:
            custom_context: 额外上下文（可选）
            
        Returns:
            查询列表（通常3-7条）
        """
        project_info = self._get_project_info()
        company_name = project_info.get("company_name", self.project_tag)
        industry = project_info.get("industry", "")
        
        templates = self.agent_config.get("query_templates", [])
        
        if not templates:
            return [f"{company_name} 投资 估值 财务 风险"]
        
        queries = []
        for template in templates:
            query = template.replace("{company_name}", company_name)
            if industry:
                query = query.replace("{industry}", industry)
            queries.append(query)
        
        if custom_context:
            queries.append(custom_context)
        
        return queries
    
    def retrieve(
        self, 
        top_k: int = None, 
        round_filter: str = "R0",
        custom_context: str = None
    ) -> List[Dict]:
        """
        执行Milvus向量检索
        
        Args:
            top_k: 返回数量（默认从配置读取，通常20）
            round_filter: 轮次过滤（R0底稿/R1/R2/R3）
            custom_context: 额外查询上下文
            
        Returns:
            相关chunk列表，按相似度排序
        """
        if top_k is None:
            top_k = self.retrieval_config.get("top_k", 20)
        
        # 构建查询
        queries = self.build_queries(custom_context)
        print(f"\n🔍 {self.agent_id} 检索策略:")
        print(f"   查询数量: {len(queries)}条")
        print(f"   目标数量: Top-{top_k}")
        print(f"   轮次过滤: {round_filter}")
        
        # 生成查询向量（取所有查询的平均）
        print(f"   正在生成查询向量...")
        query_vectors = self._get_embeddings(queries)
        
        if not query_vectors:
            print("❌ 查询向量化失败")
            return []
        
        # 平均多个查询向量
        import numpy as np
        avg_vector = np.mean(query_vectors, axis=0).tolist()
        
        # 执行Milvus检索
        print(f"   正在执行向量检索...")
        try:
            # 构建过滤表达式
            expr = f'project_tag == "{self.project_tag}"'
            if round_filter:
                expr += f' && metadata like \'"round": {round_filter}\''
            
            # 向量检索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64}
            }
            
            # 执行检索
            results = self.collection.search(
                data=[avg_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["metadata"]
            )
            
            # 解析结果
            chunks = []
            for hits in results:
                for hit in hits:
                    metadata = json.loads(hit.metadata)
                    chunk = {
                        "id": hit.id,
                        "score": hit.score,
                        "metadata": metadata,
                        "text": metadata.get("content_preview", "")
                    }
                    chunks.append(chunk)
            
            print(f"   ✅ 检索完成: {len(chunks)}个相关chunks")
            return chunks
            
        except Exception as e:
            print(f"❌ 检索失败: {e}")
            return []
    
    def format_for_agent(self, chunks: List[Dict]) -> str:
        """
        格式化为Agent可读的报告
        
        Args:
            chunks: 检索到的chunks
            
        Returns:
            格式化报告（Markdown）
        """
        if not chunks:
            return f"# {self.agent_config.get('role', 'Agent')} - 项目底稿检索\n\n⚠️ 未找到相关内容"
        
        report = f"# {self.agent_config.get('role', 'Agent')} - 项目底稿专业片段\n\n"
        
        # 项目信息
        project_info = self._get_project_info()
        report += f"**项目名称**: {project_info.get('company_name', self.project_tag)}\n"
        report += f"**检索策略**: 基于{self.agent_config.get('focus_areas', [])}关键词\n"
        report += f"**检索数量**: Top-{len(chunks)}相关片段\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        report += "---\n\n"
        
        # 按数据类型分组统计
        data_type_stats = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            dt = meta.get("data_type", meta.get("type", "general"))
            data_type_stats[dt] = data_type_stats.get(dt, 0) + 1
        
        if data_type_stats:
            report += "## 内容分布\n\n"
            for dt, count in sorted(data_type_stats.items(), key=lambda x: x[1], reverse=True):
                report += f"- **{dt}**: {count}个片段\n"
            report += "\n---\n\n"
        
        # 详细片段
        report += "## 详细片段\n\n"
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get("metadata", {})
            score = chunk.get("score", 0)
            
            report += f"### 片段 {i} (相关度: {score:.3f})\n\n"
            
            # 来源信息
            source_parts = []
            if metadata.get('file_name'):
                source_parts.append(f"文件: {metadata['file_name']}")
            if metadata.get('page'):
                source_parts.append(f"页码: {metadata['page']}")
            if metadata.get('section'):
                source_parts.append(f"章节: {metadata['section']}")
            
            if source_parts:
                report += f"**来源**: {' | '.join(source_parts)}\n\n"
            
            # 数据类型
            data_type = metadata.get('data_type', metadata.get('type', 'general'))
            report += f"**类型**: {data_type}\n\n"
            
            # 内容
            text = metadata.get("content_preview", chunk.get("text", ""))
            if text:
                report += f"{text}\n\n"
            
            report += "---\n\n"
        
        # 使用说明
        report += "## 使用说明\n\n"
        report += f"1. 以上片段基于您的专业领域（{self.agent_config.get('role')}）自动筛选\n"
        report += "2. 请基于这些片段发表您的专业观点\n"
        report += "3. 相关度分数越高表示与您的专业领域越相关\n"
        report += f"4. 完成后请将观点保存至: `projects/{self.project_tag}/10_rounds/R1/{self.agent_id}_view.md`\n"
        
        return report
    
    def save_report(self, report: str, round_num: int = 1):
        """
        保存检索报告到项目目录
        
        Args:
            report: 格式化报告
            round_num: 轮次
        """
        output_dir = os.path.expanduser(
            f"~/.openclaw/workspace/projects/{self.project_tag}/00_retrieval"
        )
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(
            output_dir, 
            f"R{round_num}_{self.agent_id}_retrieval.md"
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 检索报告已保存: {output_path}")
        return output_path
    
    def run(self, round_num: int = 1, custom_context: str = None) -> str:
        """
        执行完整检索流程
        
        Args:
            round_num: 轮次
            custom_context: 额外查询上下文
            
        Returns:
            报告路径
        """
        print(f"\n{'='*60}")
        print(f"🔍 {self.agent_config.get('role', self.agent_id)} - 底稿检索")
        print(f"{'='*60}\n")
        
        # 1. 检索
        chunks = self.retrieve(
            round_filter="R0", 
            custom_context=custom_context
        )
        
        if not chunks:
            print("⚠️ 未检索到相关内容")
            return None
        
        # 2. 格式化
        report = self.format_for_agent(chunks)
        
        # 3. 保存
        report_path = self.save_report(report, round_num)
        
        print(f"\n{'='*60}")
        print(f"✅ 检索完成: {len(chunks)}个相关片段")
        print(f"{'='*60}\n")
        
        return report_path
    
    def close(self):
        """关闭Milvus连接"""
        try:
            connections.disconnect("default")
            print("✅ Milvus连接已关闭")
        except:
            pass


def main():
    """交互式入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent专用检索器")
    parser.add_argument("--agent", required=True, help="Agent ID")
    parser.add_argument("--project", required=True, help="项目标签")
    parser.add_argument("--round", type=int, default=1, help="轮次")
    parser.add_argument("--context", help="额外查询上下文")
    
    args = parser.parse_args()
    
    # 执行检索
    retriever = AgentRetriever(
        agent_id=args.agent,
        project_tag=args.project
    )
    
    try:
        report_path = retriever.run(
            round_num=args.round,
            custom_context=args.context
        )
        
        if report_path:
            print(f"\n📄 报告已生成: {report_path}")
        else:
            print("\n⚠️ 未找到相关内容")
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
