# env_setup.py (创建milvus集合和索引的脚本)
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

MILVUS_HOST = "localhost" # 你的远端服务器地址
MILVUS_PORT = "19530"

# --- 核心修改区 ---
# 如果你的 Milvus 还没开启 GPU 支持，请保持使用 "HNSW"
# 以后开启了 GPU 支持，可切换回 "GPU_CAGRA"
USE_GPU_INDEX = False 

if USE_GPU_INDEX:
    INDEX_TYPE = "GPU_CAGRA"
    INDEX_PARAMS = {
        "metric_type": "L2",
        "index_type": INDEX_TYPE,
        "params": {
            "intermediate_graph_degree": 64,
            "graph_degree": 32,
            "efConstruction": 256
        }
    }
else:
    # 切换为高性能 CPU 索引 HNSW
    INDEX_TYPE = "HNSW"
    INDEX_PARAMS = {
        "metric_type": "L2",
        "index_type": INDEX_TYPE,
        "params": {"M": 32, "efConstruction": 256} # 针对 2560 维向量的高精度配置
    }
# ------------------

WORKSPACES = {
    "ic_chairman_ws": "投委会主席 (Nemotron-120B)",
    "ic_finance_auditor_ws": "财务审计官 (Nemotron-120B)",
    "ic_sector_expert_ws": "行业专家 (Nemotron-120B)",
    "ic_legal_scanner_ws": "法务专家 (Qwen3-32B)",
    "ic_strategist_ws": "战略专家 (Qwen3-32B)",
    "ic_risk_controller_ws": "风险官 (Qwen3-32B)",
    "ic_master_coordinator_ws": "投委会秘书 (Qwen3-32B)",
    "ic_collaboration_shared_ws": "协同共享工作区 (项目实时讨论)",
    "ic_archive_sop_ws": "机构历史案例库 (SOP资产)"
}

def init_sovereign_matrix():
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        print(f"✅ 已成功连接至 Milvus 服务器: {MILVUS_HOST}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    for col_name, desc in WORKSPACES.items():
        if utility.has_collection(col_name):
            utility.drop_collection(col_name)

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
            FieldSchema(name="project_tag", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        schema = CollectionSchema(fields, description=desc)
        collection = Collection(col_name, schema)

        # 使用修正后的索引参数
        print(f"⚙️ 正在为 {col_name} 构建 {INDEX_TYPE} 索引...")
        collection.create_index(field_name="vector", index_params=INDEX_PARAMS)
        collection.create_index(field_name="project_tag", index_params={"index_type": "INVERTED"})
        
        print(f"🚀 {col_name} 初始化完成。")

if __name__ == "__main__":
    init_sovereign_matrix()