#!/usr/bin/env python3
"""检查所有可用 collection"""

from pymilvus import MilvusClient, Collection

def main():
    print("🔍 检查 Milvus 所有集合...")
    print("="*70)
    
    try:
        # 连接到默认数据库
        client = MilvusClient(uri="http://localhost:19530")
        collections = client.list_collections()
        
        print(f"\n📚 Total Collections: {len(collections)}")
        print("-" * 70)
        
        if not collections:
            print("\n⚠️  没有找到任何 collection")
            print("   建议先运行初始化脚本创建 collection")
            return
        
        for coll_name in collections:
            try:
                coll = Collection(coll_name)
                count = coll.num_entities
                schema_fields = [f.name for f in coll.schema.fields]
                fields_info = [f"{f.name}: {f.type}" for f in coll.schema.fields]
                
                print(f"\n📄 {coll_name}")
                print(f"   ────────────────────────────────────────────────")
                print(f"   Documents: {count:,}")
                print(f"   Fields: {fields_info}")
                print(f"   ────────────────────────────────────────────────")
                
                # 显示示例数据（最多 3 条）
                if count > 0:
                    sample = coll.query(limit=3, output_fields=["*"])
                    print(f"\n   Sample Data ({len(sample)} documents):")
                    for i, doc in enumerate(sample, 1):
                        # 显示非 embedding 字段
                        text_fields = {k: v for k, v in doc.items() if k not in ['id', 'embedding']}
                        print(f"     [{i}] {text_fields}")
                        
            except Exception as e:
                print(f"\n⚠️ {coll_name}: 无法获取详细信息 - {e}")
        
        print("\n" + "="*70)
        print("✅ 检查完成!")
        
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
