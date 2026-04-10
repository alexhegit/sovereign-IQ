# unified_retriever.py
"""
Sovereign-IQ Unified High-Performance Retriever (V1.0)
---------------------------------------------------------
功能：提供跨库、跨模态的复合检索能力，支撑投委会主席的深度决策。
设计亮点：
1. 复合过滤 (Hybrid Search)：先进行 Project Tag 强过滤，再执行向量相似度检索。
2. 跨库联邦 (Cross-Coll Search)：支持同时检索“共享情报库”与“专家私有进化库”。
3. 动态索引参数：针对 HNSW 索引，提供 ef (Search Depth) 动态调优。
4. 结果重组：将碎片化的向量结果还原为具备上下文逻辑的“证据链”。
"""

import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pymilvus import connections, Collection, utility

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("UnifiedRetriever")

class SovereignRetriever:
    def __init__(self, base_url: str):
        # 初始化 OpenAI 兼容客户端 (对接本地 Qwen3-Embedding-4B)
        self.client = OpenAI(api_key="EMPTY", base_url=base_url)
        
        # 建立数据库连接
        connections.connect("default", host="localhost", port="19530")
        logger.info("✅ 统一检索模块已连接至 Milvus。")

    def _get_query_vector(self, query_text: str) -> List[float]:
        """将用户问题转化为 2048 维语义向量"""
        try:
            res = self.client.embeddings.create(
                model="fervent_mcclintock/Qwen3-VL-Embedding-2B:Q8_0",
                input=query_text
            )
            return res.data[0].embedding
        except Exception as e:
            logger.error(f"查询向量化失败: {e}")
            return []

    def hybrid_search(
        self, 
        collection_name: str, 
        query_text: str, 
        project_tag: Optional[str] = None, 
        top_k: int = 5,
        search_params: Optional[Dict] = None
    ) -> List[Dict]:
        """
        [核心接口] 执行复合检索
        project_tag: 若提供，则执行标量预过滤
        """
        if not utility.has_collection(collection_name):
            logger.warning(f"⚠️ 集合 {collection_name} 不存在")
            return []

        col = Collection(collection_name)
        col.load()

        query_vec = self._get_query_vector(query_text)
        if not query_vec: return []

        # 1. 构造标量过滤表达式
        expr = f'project_tag == "{project_tag}"' if project_tag else None

        # 2. 配置检索参数 (HNSW 动态调优)
        # ef 参数越高，召回率越高，但延迟增加。投决会关键时刻建议设为 128-256
        if search_params is None:
            search_params = {"metric_type": "L2", "params": {"ef": 128}}

        # 3. 执行向量检索
        try:
            results = col.search(
                data=[query_vec],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["metadata", "project_tag"] # 返回元数据和标签用于审计
            )
            
            output = []
            for hits in results:
                for hit in hits:
                    output.append({
                        "id": hit.id,
                        "distance": hit.distance,
                        "tag": hit.entity.get("project_tag"),
                        "metadata": hit.entity.get("metadata")
                    })
            return output
        except Exception as e:
            logger.error(f"检索执行失败: {e}")
            return []

    def cross_check_query(self, query: str, project_tag: str) -> Dict[str, List]:
        """
        [高级接口] 联邦检索：同时从事实库（Shared）和方法论库（Private）调取证据
        """
        # 1. 从协同共享库搜“当前项目事实”
        facts = self.hybrid_search("ic_collaboration_shared_ws", query, project_tag=project_tag, top_k=5)
        
        # 2. 从存档库搜“历史经验” (全局搜索，不带项目标签)
        experience = self.hybrid_search("ic_archive_sop_ws", query, project_tag=None, top_k=3)

        return {
            "project_facts": facts,
            "historical_lessons": experience
        }

# ==========================================
# 资深程序员的模拟测试接口
# ==========================================
if __name__ == "__main__":
    print("Sovereign-IQ 统一高性能检索模块启动...")
    
    retriever = SovereignRetriever(base_url="http://127.0.0.1:11434/v1")
    
    # 场景：主席 Agent 询问关于半导体光刻机项目的风险
    target_tag = "PROJECT_SEMI_2026"
    question = "该项目在核心零部件供应方面的潜在风险是什么？"
    
    # 执行联邦检索
    report = retriever.cross_check_query(question, target_tag)
    
    print(f"\n🔍 针对项目 [{target_tag}] 的检索结果：")
    print("-" * 30)
    print("📄 [项目情报事实]：")
    for fact in report["project_facts"]:
        print(f" - (得分: {fact['distance']:.4f}) {fact['metadata'].get('content_preview', '无文本内容')[:100]}...")
        
    print("\n📚 [历史经验/方法论参考]：")
    for lesson in report["historical_lessons"]:
        print(f" - (参考标签: {lesson['tag']}) 内容: {lesson['metadata'].get('content_preview', '无文本内容')[:100]}...")