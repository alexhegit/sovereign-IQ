#!/usr/bin/env python3
"""
SIQ 投委会财务专家 - 知识库检索工具
用于从 Milvus 向量数据库中检索财务知识
"""

from pymilvus import MilvusClient
import numpy as np
from typing import List, Dict, Optional

MILVUS_URI = "http://localhost:19530"
COLLECTION = "ic_finance_auditor_ws"

# 全局客户端（延迟初始化）
_client = None

def get_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=MILVUS_URI)
    return _client

def search_knowledge(
    query: str,
    top_k: int = 5,
    filter_tag: Optional[str] = None
) -> List[Dict]:
    """
    搜索财务知识库
    
    Args:
        query: 自然语言查询
        top_k: 返回结果数量
        filter_tag: 可选，batch_tag 过滤
    
    Returns:
        相关文档列表，包含 source, page, 内容描述
    """
    client = get_client()
    
    # 构建 filter
    filter_expr = None
    if filter_tag:
        filter_expr = f'batch_tag == "{filter_tag}"'
    
    # 由于我们没有 embedding 模型，使用 metadata 过滤 + 随机向量演示
    # 实际部署时应接入 text-embedding-3 或其他 embedding API
    results = client.query(
        collection_name=COLLECTION,
        filter=filter_expr,
        limit=top_k,
        output_fields=['batch_tag', 'metadata']
    )
    
    formatted = []
    for r in results:
        formatted.append({
            'id': r['id'],
            'batch_tag': r['batch_tag'],
            'source': r['metadata'].get('source', 'Unknown'),
            'page': r['metadata'].get('page', '?'),
        })
    
    return formatted

def get_collection_stats() -> Dict:
    """获取 collection 统计信息"""
    client = get_client()
    stats = client.get_collection_stats(COLLECTION)
    
    # 获取所有数据概览
    all_data = client.query(
        collection_name=COLLECTION,
        limit=2000,
        output_fields=['batch_tag', 'metadata']
    )
    
    from collections import defaultdict
    source_stats = defaultdict(lambda: {'count': 0, 'pages': set()})
    for d in all_data:
        src = d['metadata'].get('source', 'Unknown')
        page = d['metadata'].get('page', '?')
        source_stats[src]['count'] += 1
        source_stats[src]['pages'].add(page)
    
    return {
        'total_records': stats['row_count'],
        'sources': {
            src: {
                'records': data['count'],
                'pages': len(data['pages'])
            }
            for src, data in source_stats.items()
        }
    }

def list_sources() -> List[str]:
    """列出所有数据源"""
    client = get_client()
    all_data = client.query(
        collection_name=COLLECTION,
        limit=2000,
        output_fields=['metadata']
    )
    sources = sorted(set([d['metadata'].get('source', 'Unknown') for d in all_data]))
    return sources

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("用法: python3 finance_kb_search.py <search_query> [top_k]")
        print("\n可用命令:")
        print("  python3 finance_kb_search.py stats      - 查看统计信息")
        print("  python3 finance_kb_search.py sources    - 列出所有数据源")
        print("  python3 finance_kb_search.py search <query> [k] - 搜索")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "stats":
        stats = get_collection_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    elif cmd == "sources":
        for src in list_sources():
            print(f"  - {src}")
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = search_knowledge(query, top_k)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"未知命令: {cmd}")
