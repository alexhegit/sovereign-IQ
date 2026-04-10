#!/usr/bin/env python3
"""Milvus 数据库连接和知识库检查脚本"""

from pymilvus import MilvusClient, Collection

def main():
    print("=== 数据库连接状态 ===")
    
    # 先连接到默认数据库，查看有哪些 database 可用
    try:
        temp_client = MilvusClient(uri="http://localhost:19530")
        print("✅ Connected to Milvus default")
        
        # 列出所有 database
        try:
            from pymilvus import connections
            connections.connect('default', host='localhost', port=19530)
            from milvus import MilvusDB
            result = connections.list_databases()
            if hasattr(result, 'dbs'):
                print(f"\n📁 Available Databases ({len(result.dbs)}):")
                for db in result.dbs:
                    print(f"  • {db.name}")
            else:
                print("\n📁 无法列出数据库列表")
        except Exception as db_error:
            print(f"\n📁 无法列出数据库：{db_error}")
        
        # 尝试连接到共享工作区数据库
        try:
            client = MilvusClient(
                uri="http://localhost:19530",
                db_name="ic_collaboration_shared_ws"
            )
            print("\n✅ Connected to ic_collaboration_shared_ws")
            
            # 列出所有 collection
            collections = client.list_collections()
            print(f"\n📁 Available Collections ({len(collections)}):")
            for coll in collections:
                print(f"  • {coll}")
            
            # 获取每个 collection 的详细统计
            print("\n📊 Collection Details:")
            for coll_name in collections:
                try:
                    coll = Collection(coll_name)
                    count = coll.num_entities
                    schema_fields = [f.name for f in coll.schema.fields]
                    print(f"  → {coll_name}:")
                    print(f"      Documents: {count:,}")
                    print(f"      Fields: {', '.join(schema_fields)}")
                except Exception as e:
                    print(f"  → {coll_name}: 无法获取详细信息 - {e}")
            
        except Exception as e:
            print(f"\n❌ Error connecting to ic_collaboration_shared_ws: {e}")
            print("   尝试切换到 default database...")
            
            # 如果没有该数据库，尝试使用 default database
            try:
                client = MilvusClient(
                    uri="http://localhost:19530",
                    db_name="default"
                )
                collections = client.list_collections()
                print(f"\n📁 Available Collections in 'default' ({len(collections)}):")
                for coll in collections:
                    print(f"  • {coll}")
                
                print("\n📊 Collection Details in 'default':")
                for coll_name in collections:
                    try:
                        coll = Collection(coll_name)
                        count = coll.num_entities
                        schema_fields = [f.name for f in coll.schema.fields]
                        print(f"  → {coll_name}:")
                        print(f"      Documents: {count:,}")
                        print(f"      Fields: {', '.join(schema_fields)}")
                    except Exception as e:
                        print(f"  → {coll_name}: 无法获取详细信息 - {e}")
            except Exception as e2:
                print(f"❌ 无法连接到 default database: {e2}")
        
    except Exception as e:
        print(f"❌ Error in database operations: {e}")
        return
    
    print("\n" + "="*70)
    
    # 连接个人知识库
    print("🔍 Personal Knowledge Base: ic_chairman")
    print("="*70)
    
    try:
        # 先连接到默认数据库
        my_client = MilvusClient(uri="http://localhost:19530")
        all_collections = my_client.list_collections()
        
        # 筛选出与 ic_chairman 相关的 collection
        chair_collections = [c for c in all_collections if 'ic_chairman' in c.lower()]
        
        if chair_collections:
            print(f"\n📚 Personal Knowledge Collections ({len(chair_collections)}):")
            for coll_name in chair_collections:
                try:
                    coll = Collection(coll_name)
                    count = coll.num_entities
                    schema_fields = [f.name for f in coll.schema.fields]
                    print(f"  • {coll_name}")
                    print(f"      Documents: {count:,}")
                    print(f"      Fields: {', '.join(schema_fields)}")
                    
                    # 显示一些示例文档
                    if count > 0:
                        sample = coll.query(limit=1)
                        if sample:
                            doc = sample[0]
                            fields = [k for k in doc.keys() if k not in ['id', 'embedding']]
                            print(f"      Sample fields: {', '.join(fields[:5])}")
                except Exception as e:
                    print(f"  ✗ {coll_name}: {e}")
        else:
            print("\n⚠️ 未找到与 ic_chairman 相关的知识库")
            print("   建议：使用 sessions_spawn 进行深度学习配置")
        
    except Exception as e:
        print(f"❌ Error accessing personal knowledge base: {e}")

if __name__ == "__main__":
    main()
