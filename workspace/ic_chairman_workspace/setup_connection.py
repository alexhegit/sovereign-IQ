#!/usr/bin/env python3
"""设置 ic_chairman 连接的脚本"""

from pymilvus import MilvusClient, Collection, connections

def setup_chairman_connection():
    """建立 ic_chairman 到 ic_chairman_ws 的连接"""
    
    # 首先建立连接别名
    print("🔧 设置连接别名...")
    try:
        connections.connect(
            alias="ic_chairman",
            host="localhost",
            port="19530",
            user="root",
            password="Milvus"
        )
        print("✅ 连接别名已创建：ic_chairman")
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        return
    
    # 连接到个人知识库
    print("\n🔍 连接到 ic_chairman_ws...")
    try:
        client = MilvusClient(
            uri="http://localhost:19530",
            alias="ic_chairman"
        )
        
        collections = client.list_collections()
        print(f"📚 Available Collections: {collections}")
        
        # 检查是否有 chairman_ws collection
        if "ic_chairman_ws" in collections:
            print("\n✅ 找到 ic_chairman_ws collection!")
            
            # 查看详细信息
            coll = Collection("ic_chairman_ws")
            count = coll.num_entities
            schema_fields = [f"{f.name}: {f.type.name}" for f in coll.schema.fields]
            
            print(f"\n📄 Collection 详情:")
            print(f"  Documents: {count:,}")
            print(f"  Fields: {', '.join(schema_fields)}")
            
            # 显示示例数据
            if count > 0:
                print(f"\n📋 示例数据 (前 5 条):")
                sample = coll.query(limit=5, output_fields=["*"])
                for i, doc in enumerate(sample, 1):
                    text_fields = {k: v for k, v in doc.items() if k not in ['id', 'embedding']}
                    # 截取短字段显示
                    display = {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                              for k, v in text_fields.items()}
                    print(f"    [{i}] {display}")
            
            print(f"\n✅ 连接设置完成!")
            return True
        else:
            print(f"\n⚠️  未找到 ic_chairman_ws collection")
            print("   建议创建该 collection 并导入知识文档")
            return False
            
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_chairman_connection()
