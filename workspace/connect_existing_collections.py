#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIQ 投委会 - 连接现有 Collections（包含 ic_master_coordinator）

Agent 与 Collections 完全匹配连接
"""

from pymilvus import connections, Collection, utility

# Agent 配置（包含 ic_master_coordinator）
AGENTS = {
    "ic_finance_auditor": "SIQ 投委会财务专家",
    "ic_legal_scanner": "SIQ 投委会法务专家",
    "ic_sector_expert": "SIQ 投委会行业专家",
    "ic_strategist": "SIQ 投委会战略专家",
    "ic_risk_controller": "SIQ 投委会风控委员",
    "ic_chairman": "SIQ 投委会主席",
    "ic_master_coordinator": "SIQ 投委会秘书/协调者"  # 新增
}


def connect_to_agent_collection(agent_id: str):
    """
    连接到 Agent 对应的 Collection
    
    Returns:
        Collection 对象或 None
    """
    try:
        # 连接 Milvus
        if not connections.has_connection("default"):
            connections.connect(host="localhost", port=19530)
        
        # Collection 名称 = Agent ID + "_ws"
        collection_name = f"{agent_id}_ws"
        
        # 检查 Collection 是否存在
        if not utility.has_collection(collection_name):
            print(f"  ⚠️  Collection '{collection_name}' 不存在，跳过")
            return None
        
        # 加载 Collection
        collection = Collection(collection_name)
        collection.load()
        
        print(f"  ✅ {agent_id}")
        print(f"     Collection: {collection_name}")
        print(f"     实体数量：{collection.num_entities}")
        print(f"     字段：{[f.name for f in collection.schema.fields]}")
        print(f"     索引：{[idx.index_name for idx in collection.indexes]}")
        
        return collection
        
    except Exception as e:
        print(f"  ❌ {agent_id}: {e}")
        return None


def main():
    """主函数"""
    
    print("=" * 80)
    print("SIQ Investment Committee - 连接现有 Collections")
    print("=" * 80)
    print()
    
    # 连接 Milvus
    try:
        connections.connect(host="localhost", port=19530)
        print("✅ 连接到 Milvus 服务器成功\n")
    except Exception as e:
        print(f"❌ 连接 Milvus 失败：{e}")
        return
    
    # 列出所有 Collections
    all_collections = utility.list_collections()
    print("📋 现有 Collections:")
    for coll in all_collections:
        print(f"   • {coll}")
    print()
    
    # 为每个 Agent 连接对应的 Collection
    print("=" * 80)
    print("Agent 连接状态:")
    print("=" * 80)
    
    results = {}
    
    for agent_id in sorted(AGENTS.keys()):
        collection = connect_to_agent_collection(agent_id)
        results[agent_id] = collection
    
    # 总结
    print()
    print("=" * 80)
    print("连接统计:")
    print("=" * 80)
    
    total_agents = len(AGENTS)
    connected_agents = sum(1 for c in results.values() if c)
    
    print(f"  总 Agent 数：{total_agents}")
    print(f"  成功连接：{connected_agents}/{total_agents}")
    print(f"  失败/未连接：{total_agents - connected_agents}/{total_agents}")
    
    print()
    print("连接详情:")
    for agent_id, collection in results.items():
        status = "✅" if collection else "❌"
        print(f"  {status} {agent_id} ({AGENTS[agent_id]})")
    
    print("=" * 80)
    
    # 返回成功连接的集合
    return {agent_id: coll for agent_id, coll in results.items() if coll}


if __name__ == "__main__":
    main()
