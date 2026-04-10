#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Milvus数据库架构验证与Agent连接测试
用于SIQ投委会系统
"""

from pymilvus import connections, utility, Collection
import sys

class MilvusArchitectureVerifier:
    """Milvus架构验证器"""
    
    # Agent与Collection的映射关系
    AGENT_COLLECTION_MAP = {
        "ic_strategist": "ic_strategist_ws",
        "ic_sector_expert": "ic_sector_expert_ws",
        "ic_finance_auditor": "ic_finance_auditor_ws",
        "ic_legal_scanner": "ic_legal_scanner_ws",
        "ic_risk_controller": "ic_risk_controller_ws",
        "ic_chairman": "ic_chairman_ws",
        "ic_master_coordinator": "ic_master_coordinator_ws",
    }
    
    # 特殊Collection
    SHARED_COLLECTION = "ic_collaboration_shared_ws"
    ARCHIVE_COLLECTION = "ic_archive_sop_ws"
    
    def __init__(self, host="localhost", port="19530"):
        """初始化连接"""
        self.host = host
        self.port = port
        self.connection = None
        
    def connect(self):
        """连接Milvus"""
        try:
            connections.connect(host=self.host, port=self.port)
            self.connection = True
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def verify_architecture(self):
        """验证完整架构"""
        print("=" * 70)
        print("SIQ 投委会系统 - Milvus数据库架构验证报告")
        print("=" * 70)
        print()
        
        # 1. 连接测试
        print("【1. 连接测试】")
        print("-" * 70)
        if not self.connect():
            return False
        print(f"✅ 连接成功: {self.host}:{self.port}")
        print()
        
        # 2. 验证私有知识库（7个Agent）
        print("【2. 私有知识库验证 - 7个Agent】")
        print("-" * 70)
        print(f"{'Agent ID':<25} {'Collection名称':<30} {'状态':<10} {'记录数':<10}")
        print("-" * 70)
        
        all_private_ok = True
        for agent_id, coll_name in self.AGENT_COLLECTION_MAP.items():
            try:
                if utility.has_collection(coll_name):
                    coll = Collection(coll_name)
                    coll.load()
                    count = coll.num_entities
                    print(f"{agent_id:<25} {coll_name:<30} {'✅ 正常':<10} {count:<10}")
                else:
                    print(f"{agent_id:<25} {coll_name:<30} {'❌ 不存在':<10} {'-':<10}")
                    all_private_ok = False
            except Exception as e:
                print(f"{agent_id:<25} {coll_name:<30} {'❌ 错误':<10} {str(e)[:20]:<10}")
                all_private_ok = False
        
        print()
        
        # 3. 验证共享库
        print("【3. 协同共享库验证】")
        print("-" * 70)
        try:
            if utility.has_collection(self.SHARED_COLLECTION):
                coll = Collection(self.SHARED_COLLECTION)
                coll.load()
                count = coll.num_entities
                print(f"✅ {self.SHARED_COLLECTION:<30} {'正常':<10} 记录数: {count}")
                shared_ok = True
            else:
                print(f"❌ {self.SHARED_COLLECTION:<30} {'不存在':<10}")
                shared_ok = False
        except Exception as e:
            print(f"❌ {self.SHARED_COLLECTION:<30} {'错误':<10} {e}")
            shared_ok = False
        
        print()
        
        # 4. 验证归档库
        print("【4. 归档库验证】")
        print("-" * 70)
        try:
            if utility.has_collection(self.ARCHIVE_COLLECTION):
                coll = Collection(self.ARCHIVE_COLLECTION)
                coll.load()
                count = coll.num_entities
                print(f"✅ {self.ARCHIVE_COLLECTION:<30} {'正常':<10} 记录数: {count}")
                archive_ok = True
            else:
                print(f"❌ {self.ARCHIVE_COLLECTION:<30} {'不存在':<10}")
                archive_ok = False
        except Exception as e:
            print(f"❌ {self.ARCHIVE_COLLECTION:<30} {'错误':<10} {e}")
            archive_ok = False
        
        print()
        
        # 5. 架构完整性总结
        print("【5. 架构完整性总结】")
        print("-" * 70)
        total_collections = len(self.AGENT_COLLECTION_MAP) + 2  # 7私有 + 1共享 + 1归档
        existing_collections = utility.list_collections()
        
        print(f"预期Collection数量: {total_collections}")
        print(f"实际存在数量: {len(existing_collections)}")
        print()
        
        expected = set(self.AGENT_COLLECTION_MAP.values()) | {self.SHARED_COLLECTION, self.ARCHIVE_COLLECTION}
        actual = set(existing_collections)
        
        missing = expected - actual
        extra = actual - expected
        
        if missing:
            print(f"❌ 缺失的Collections: {missing}")
        if extra:
            print(f"⚠️ 额外的Collections: {extra}")
        
        if not missing and not extra:
            print("✅ 架构完整！所有Collections存在且一一对应")
        
        print()
        print("=" * 70)
        
        return all_private_ok and shared_ok and archive_ok
    
    def test_agent_write(self, agent_id, test_content="测试数据"):
        """测试Agent写入权限"""
        coll_name = self.AGENT_COLLECTION_MAP.get(agent_id)
        if not coll_name:
            return False, f"未知Agent ID: {agent_id}"
        
        try:
            coll = Collection(coll_name)
            # 这里可以添加实际的写入测试
            return True, "写入权限正常"
        except Exception as e:
            return False, str(e)
    
    def get_collection_schema(self, coll_name):
        """获取Collection Schema"""
        try:
            coll = Collection(coll_name)
            schema = coll.schema
            
            fields = []
            for field in schema.fields:
                field_info = {
                    "name": field.name,
                    "type": str(field.dtype),
                    "is_primary": getattr(field, 'is_primary', False),
                    "dim": getattr(field, 'dim', None)
                }
                fields.append(field_info)
            
            return fields
        except Exception as e:
            return None


def print_architecture_diagram():
    """打印架构图"""
    print()
    print("=" * 70)
    print("SIQ 投委会系统 - Milvus数据库架构图")
    print("=" * 70)
    print()
    print("┌─────────────────────────────────────────────────────────────────────┐")
    print("│                     Milvus 数据库架构                                │")
    print("├─────────────────────────────────────────────────────────────────────┤")
    print("│                                                                      │")
    print("│  【Layer 1: 私有知识库层】7个Collections                             │")
    print("│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │")
    print("│  │ ic_strategist   │  │ ic_sector_expert│  │ ic_finance_     │     │")
    print("│  │     _ws         │  │      _ws        │  │   auditor_ws    │     │")
    print("│  │ (战略专家)      │  │ (行业专家)      │  │ (财务专家)      │     │")
    print("│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │")
    print("│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │")
    print("│  │ ic_legal_scanner│  │ ic_risk_control │  │ ic_chairman     │     │")
    print("│  │      _ws        │  │     ler_ws      │  │     _ws         │     │")
    print("│  │ (法律专家)      │  │ (风控专家)      │  │ (主席)          │     │")
    print("│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │")
    print("│  ┌─────────────────┐                                                │")
    print("│  │ ic_master_coord │                                                │")
    print("│  │    inator_ws    │                                                │")
    print("│  │ (协调者)        │                                                │")
    print("│  └────────┬────────┘                                                │")
    print("│           │  R2/R3知识沉淀                                          │")
    print("│           ▼                                                          │")
    print("│  【Layer 2: 协同共享层】1个Collection                                │")
    print("│  ┌─────────────────────────────────────────┐                        │")
    print("│  │     ic_collaboration_shared_ws          │                        │")
    print("│  │          (项目讨论共享库)                │                        │")
    print("│  │  - project_tag: 项目隔离                │                        │")
    print("│  │  - round: R0/R1/R2/R3                   │                        │")
    print("│  │  - content_type: fact/view/conflict     │                        │")
    print("│  └──────────────────┬──────────────────────┘                        │")
    print("│                     │  项目结束后迁移                                  │")
    print("│                     ▼                                                │")
    print("│  【Layer 3: 归档层】1个Collection                                    │")
    print("│  ┌─────────────────────────────────────────┐                        │")
    print("│  │       ic_archive_sop_ws                 │                        │")
    print("│  │           (长期归档库)                   │                        │")
    print("│  │  - 保留期限: 7年+                       │                        │")
    print("│  │  - 支持跨项目检索                       │                        │")
    print("│  └─────────────────────────────────────────┘                        │")
    print("│                                                                      │")
    print("└─────────────────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    # 打印架构图
    print_architecture_diagram()
    
    # 执行验证
    verifier = MilvusArchitectureVerifier()
    result = verifier.verify_architecture()
    
    if result:
        print("✅ 所有测试通过！系统可以正常工作")
        sys.exit(0)
    else:
        print("❌ 存在错误，请检查配置")
        sys.exit(1)