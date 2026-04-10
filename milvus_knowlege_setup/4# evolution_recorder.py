# evolution_recorder.py
"""
Sovereign-IQ Evolution Recorder (V1.0 - Production Grade)
---------------------------------------------------------
功能：
1. 过程存证：实时记录投决会讨论细节，存入共享工作区（Shared WS）。
2. 逻辑进化：识别高价值观点，将其“升维”回传至专家的私有知识库（Private WS）。
3. 知识主权：严格区分“项目事实”与“通用逻辑”，实现 Agent 的差异化成长。

设计模式：
- Observer Pattern（观察者模式）：监听讨论流。
- Strategy Pattern（策略模式）：根据发言者动态切换存储目标。
"""

import os
import json
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 核心依赖
from openai import OpenAI
from pymilvus import connections, Collection, utility

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("EvolutionRecorder")

class EvolutionRecorder:
    """
    Sovereign-IQ 决策进化记录器：负责对话存证与知识回传。
    """
    
    # 角色库映射（用于知识回传目标定向）
    AGENT_WS_MAP = {
        "chairman": "ic_chairman_ws",
        "auditor": "ic_finance_auditor_ws",
        "sector_expert": "ic_sector_expert_ws",
        "legal": "ic_legal_scanner_ws",
        "strategist": "ic_strategist_ws",
        "risk_controller": "ic_risk_controller_ws",
        "secretary": "ic_master_coordinator_ws"
    }

    def __init__(self, base_url: str, shared_ws: str = "ic_collaboration_shared_ws"):
        self.client = OpenAI(api_key="EMPTY", base_url=base_url)
        self.shared_ws = shared_ws
        
        # 初始化连接
        connections.connect("default", host="localhost", port="19530")
        self.shared_col = Collection(self.shared_ws)
        self.shared_col.load()
        logger.info(f"✅ 进化记录器已就绪，挂载共享区: {shared_ws}")

    def _get_embedding(self, text: str) -> List[float]:
        """调用本地 Qwen3-VL-Embedding-2B 获取 2048 维向量"""
        try:
            res = self.client.embeddings.create(
                model="fervent_mcclintock/Qwen3-VL-Embedding-2B:Q8_0",
                input=[text]
            )
            return res.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding 失败: {e}")
            return []

    def record_discussion(self, agent_id: str, project_tag: str, content: str, is_methodology: bool = False):
        """
        [核心接口] 记录一条发言，并判断是否需要执行双向存储。
        
        agent_id: 发言者 ID (如 'auditor')
        project_tag: 项目标签 (如 '2026_SEMI_001')
        content: 发言原始文本
        is_methodology: 秘书/主席是否判定该观点具有方法论进化价值
        """
        # 1. 生成语义向量
        vector = self._get_embedding(content)
        if not vector: return

        # 2. 存入协同共享库 (记录讨论过程 - Fact Trace)
        shared_meta = {
            "agent_id": agent_id,
            "project_tag": project_tag,
            "type": "discussion_log",
            "timestamp": time.time(),
            "content": content[:1000] # 存储截断用于预览
        }
        
        try:
            self.shared_col.insert([
                [vector],
                [project_tag],
                [shared_meta]
            ])
            logger.info(f"🎙️ [Log] {agent_id} 的发言已存证于共享区。")
        except Exception as e:
            logger.error(f"共享区存证失败: {e}")

        # 3. 双向存储逻辑：回传专家私有库 (进化进化 - Methodology Crystallization)
        if is_methodology:
            self._crystallize_to_private(agent_id, project_tag, content, vector)

    def _crystallize_to_private(self, agent_id: str, source_tag: str, content: str, vector: List[float]):
        """将有价值的逻辑回传至对应的专家私有库"""
        target_ws = self.AGENT_WS_MAP.get(agent_id)
        if not target_ws:
            logger.warning(f"⚠️ 未找到 Agent {agent_id} 的私有库，跳过回传。")
            return

        try:
            private_col = Collection(target_ws)
            # 私有库 Metadata 更强调“方法论”属性
            private_meta = {
                "knowledge_type": "evolved_logic",
                "source_project": source_tag,
                "crystallized_at": datetime.now().isoformat(),
                "logic_body": content
            }
            
            private_col.insert([
                [vector],
                [source_tag],
                [private_meta]
            ])
            private_col.flush() # 强制落盘，确保逻辑立即生效
            logger.info(f"✨ [Evolve] 高价值逻辑已回传至 {target_ws}。")
        except Exception as e:
            logger.error(f"知识回传失败: {e}")

# ==========================================
# 资深程序员的模拟测试接口
# ==========================================
if __name__ == "__main__":
    print("Sovereign-IQ 决策进化与双向存储引擎启动...")
    
    recorder = EvolutionRecorder(base_url="http://127.0.0.1:11434/v1")
    
    # 模拟讨论场景：财务审计官提出一个通用的 ROE 修正逻辑
    p_tag = "PROJECT_SEMI_2026"
    
    # 案例 1：普通过程记录
    recorder.record_discussion(
        agent_id="auditor",
        project_tag=p_tag,
        content="根据当前底稿，该公司的现金流在 Q3 有异常波动，建议法务交叉核对合同。"
    )
    
    # 案例 2：高价值方法论回传（由秘书 Agent 判定为 True）
    recorder.record_discussion(
        agent_id="auditor",
        project_tag=p_tag,
        content="针对半导体初创公司，我们应建立‘专利密度/流片成本’的效能评估模型，而非传统 PE 估值。",
        is_methodology=True
    )