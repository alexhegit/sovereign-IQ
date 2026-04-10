"""
Milvus知识库连接工具 - ic_sector_expert_ws
机器人行业研究报告知识库

连接信息:
- Host: localhost
- Port: 19530
- Collection: ic_sector_expert_ws
- 向量维度: 1024
- 度量类型: IP (Inner Product)
"""

from pymilvus import connections, Collection
from pymilvus.exceptions import MilvusException
import numpy as np
import json

# 连接配置
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "ic_sector_expert_ws"
VECTOR_DIMENSION = 1024
METRIC_TYPE = "IP"  # Inner Product

def get_connection(timeout: float = 30.0):
    """建立Milvus连接"""
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT, alias="default", timeout=timeout)

def close_connection():
    """关闭Milvus连接"""
    connections.disconnect("default")

def search_knowledge_base(query_text: str, top_k: int = 10, batch_tag: str = None, return_content: bool = True):
    """
    搜索知识库
    
    Args:
        query_text: 查询文本
        top_k: 返回前k条结果
        batch_tag: 可选，按batch_tag过滤
        return_content: 是否返回content字段
    
    Returns:
        list: 搜索结果列表
    """
    get_connection()
    
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        
        # 生成查询向量 (使用随机向量演示，实际应用需要文本嵌入模型)
        # 实际使用时需要用文本嵌入模型如 sentence-transformers 生成向量
        query_vector = np.random.randn(VECTOR_DIMENSION).astype(np.float32).tolist()
        
        # 搜索参数
        search_params = {"metric_type": METRIC_TYPE, "params": {"nprobe": 64}}
        
        # 搜索表达式
        expr = None
        if batch_tag:
            expr = f'batch_tag == "{batch_tag}"'
        
        # 执行搜索
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["id", "batch_tag", "metadata"]
        )
        
        # 整理结果
        search_results = []
        for hits in results:
            for hit in hits:
                metadata = hit.entity.get("metadata", {})
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                
                result = {
                    "id": hit.id,
                    "score": hit.distance,
                    "batch_tag": hit.entity.get("batch_tag"),
                    "source": metadata.get("source", ""),
                }
                
                if return_content:
                    result["content"] = metadata.get("content", "")
                
                search_results.append(result)
        
        return search_results
        
    except MilvusException as e:
        print(f"Milvus搜索错误: {e}")
        return []
    finally:
        close_connection()

def search_with_text_vector(query_vector: list, top_k: int = 10, batch_tag: str = None):
    """
    使用已有向量搜索知识库
    
    Args:
        query_vector: 查询向量 (1024维)
        top_k: 返回前k条结果
        batch_tag: 可选，按batch_tag过滤
    
    Returns:
        list: 搜索结果列表
    """
    get_connection()
    
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        
        # 搜索参数
        search_params = {"metric_type": METRIC_TYPE, "params": {"nprobe": 64}}
        
        # 搜索表达式
        expr = None
        if batch_tag:
            expr = f'batch_tag == "{batch_tag}"'
        
        # 执行搜索
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["id", "batch_tag", "metadata"]
        )
        
        # 整理结果
        search_results = []
        for hits in results:
            for hit in hits:
                metadata = hit.entity.get("metadata", {})
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                
                search_results.append({
                    "id": hit.id,
                    "score": hit.distance,
                    "batch_tag": hit.entity.get("batch_tag"),
                    "metadata": metadata,
                    "source": metadata.get("source", ""),
                    "content": metadata.get("content", "")
                })
        
        return search_results
        
    except MilvusException as e:
        print(f"Milvus搜索错误: {e}")
        return []
    finally:
        close_connection()

def query_by_id(doc_id: int):
    """
    根据ID查询文档
    
    Args:
        doc_id: 文档ID
    
    Returns:
        dict: 文档内容
    """
    get_connection()
    
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        
        results = collection.query(
            expr=f"id == {doc_id}",
            limit=1,
            output_fields=["id", "batch_tag", "metadata"]
        )
        
        if results:
            metadata = results[0].get("metadata", {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            return {
                "id": results[0]["id"],
                "batch_tag": results[0]["batch_tag"],
                "metadata": metadata,
                "source": metadata.get("source", ""),
                "content": metadata.get("content", "")
            }
        
        return None
        
    except MilvusException as e:
        print(f"Milvus查询错误: {e}")
        return None
    finally:
        close_connection()

def get_collection_stats():
    """获取collection统计信息"""
    from pymilvus import utility
    
    get_connection()
    
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        
        stats = {
            "collection_name": COLLECTION_NAME,
            "entities_count": collection.num_entities,
            "vector_dimension": VECTOR_DIMENSION,
            "metric_type": METRIC_TYPE,
            "index_status": utility.index_building_progress(COLLECTION_NAME),
        }
        
        return stats
        
    except MilvusException as e:
        print(f"获取统计信息错误: {e}")
        return {}
    finally:
        close_connection()

def list_batch_tags():
    """列出所有可用的batch_tag"""
    get_connection()
    
    try:
        collection = Collection(COLLECTION_NAME)
        collection.load()
        
        # 查询所有不同的batch_tag
        results = collection.query(
            expr="id > 0",
            limit=1000,
            output_fields=["batch_tag"]
        )
        
        batch_tags = set()
        for r in results:
            if r.get("batch_tag"):
                batch_tags.add(r["batch_tag"])
        
        return sorted(list(batch_tags))
        
    except MilvusException as e:
        print(f"获取batch_tag错误: {e}")
        return []
    finally:
        close_connection()

# 测试连接
if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Milvus知识库连接测试")
    print("=" * 50)
    
    # 获取统计信息
    print("\n📊 Collection统计:")
    stats = get_collection_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    # 列出batch_tags
    print("\n📚 可用Batch Tags:")
    tags = list_batch_tags()
    for tag in tags[:10]:
        print(f"   - {tag}")
    if len(tags) > 10:
        print(f"   ... 等共 {len(tags)} 个")
    
    # 执行示例搜索
    print("\n🔍 示例搜索 (人形机器人):")
    results = search_knowledge_base("人形机器人市场规模", top_k=3)
    for i, r in enumerate(results):
        print(f"\n   --- 结果 {i+1} (Score: {r['score']:.4f}) ---")
        print(f"   Source: {r['source'][:80]}...")
        if r.get('content'):
            print(f"   Content: {r['content'][:150]}...")
    
    print("\n" + "=" * 50)
    print("✅ 知识库连接测试完成!")
    print("=" * 50)