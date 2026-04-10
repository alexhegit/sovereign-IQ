#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sovereign-IQ Secretary Supplement - 秘书情报补充技能 (V1.0)
---------------------------------------------------------
功能：秘书Agent接收人类指令后，自动从外部数据源抓取补充信息

工作流程：
1. 接收人类指令（通过飞书/消息）
2. 从共享库读取最新入库的底稿
3. 调用外部数据源补充信息（企查查/Tavily等）
4. 检测信息冲突
5. 向量化后写入共享库
6. 如有冲突，发出告警

外部数据源：
- 企查查API：工商信息、股东结构、融资历史
- Tavily API：新闻、融资动态、行业信息
"""

import os
import json
import time
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

# 第三方库
from pymilvus import connections, Collection, utility
from openai import OpenAI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("SecretarySupplement")

# ============================================================================
# 常量配置
# ============================================================================

SHARED_COLLECTION = "ic_collaboration_shared_ws"
VECTOR_DIM = 1024
EMBEDDING_API = "http://127.0.0.1:11434/v1"
EMBEDDING_MODEL = "qwen3-vl-embedding"

# 外部数据源配置（支持多源交叉验证）
DATA_SOURCES = {
    "qcc": {
        "name": "企查查",
        "api_token": "M4WAY2HB1uf5nYN6xZjMpiBKDTtyr8uNYJf5EsqoWi3FKloI",
        "type": "工商信息",
        "reliability": "high"  # 权威工商数据
    },
    "tavily": {
        "name": "Tavily",
        "api_key": "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",
        "type": "新闻资讯/公开信息",
        "reliability": "medium"  # 搜索引擎聚合
    },
    # 可扩展更多数据源
    # "tianyancha": {...},
    # "official_announcement": {...},
}

# 关键验证字段（用于多源交叉验证）
VALIDATION_FIELDS = [
    "valuation",         # 估值
    "funding_amount",    # 融资金额
    "company_name",      # 公司名称
    "team_size",         # 团队规模
    "established_date",  # 成立日期
    "revenue",           # 营收
    "market_share",      # 市场份额
]

# ============================================================================
# 秘书技能类
# ============================================================================

class SecretarySupplement:
    """
    秘书情报补充技能
    
    职责：
    1. 从共享库读取最新底稿
    2. 调用外部数据源抓取补充信息
    3. 检测信息冲突
    4. 向量化后写入共享库
    """
    
    def __init__(self, base_url: str = EMBEDDING_API):
        self.base_url = base_url
        self.vector_dim = VECTOR_DIM
        
        # 初始化向量化客户端
        self.client = OpenAI(api_key="EMPTY", base_url=base_url)
        
        # 初始化数据库连接
        self._init_milvus()
    
    def _init_milvus(self):
        """连接Milvus共享库"""
        try:
            connections.connect("default", host="localhost", port="19530")
            self.collection = Collection(SHARED_COLLECTION)
            self.collection.load()
            logger.info(f"✅ 已挂载共享库: {SHARED_COLLECTION}")
        except Exception as e:
            logger.error(f"❌ Milvus连接失败: {e}")
            raise
    
    # =========================================================================
    # 外部数据源接口
    # =========================================================================
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """调用向量化接口"""
        formatted = [{"type": "text", "text": t} for t in texts]
        
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=formatted,
                timeout=60.0
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            logger.error(f"❌ 向量化失败: {e}")
            return []
    
    def fetch_qcc_data(self, company_name: str) -> Dict:
        """
        从企查查获取公司工商信息（结构化）
        
        Args:
            company_name: 公司名称
            
        Returns:
            结构化公司信息 {"source": "qcc", "data": {...}}
        """
        try:
            url = "https://api.qcc.com/api/firm/data"
            headers = {"token": DATA_SOURCES["qcc"]["api_token"]}
            params = {"name": company_name}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 企查查获取成功: {company_name}")
                return {
                    "source": "qcc",
                    "source_name": "企查查",
                    "reliability": "high",
                    "raw_data": data.get("data", {}),
                    "structured": self._structure_qcc_data(data.get("data", {}))
                }
            else:
                logger.warning(f"⚠️ 企查查请求失败: {response.status_code}")
                return {"source": "qcc", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"❌ 企查查异常: {e}")
            return {"source": "qcc", "error": str(e)}
    
    def _structure_qcc_data(self, raw_data: Dict) -> Dict:
        """将企查查原始数据转为结构化格式"""
        structured = {}
        
        # 提取关键验证字段
        if raw_data.get("Name"):
            structured["company_name"] = raw_data.get("Name")
        if raw_data.get("EstiblishTime"):
            structured["established_date"] = raw_data.get("EstiblishTime")
        if raw_data.get("Capital"):
            structured["capital"] = raw_data.get("Capital")
        if raw_data.get("EmployeeNum"):
            structured["team_size"] = raw_data.get("EmployeeNum")
        
        # 估值相关（如果有）
        if raw_data.get("Financing"):
            financing = raw_data.get("Financing", [])
            if financing:
                latest = financing[0]  # 最近一轮
                structured["last_funding_round"] = latest.get("Round", "")
                structured["funding_amount"] = latest.get("Amount", "")
        
        return structured
    
    def fetch_tavily_data(self, company_name: str, data_type: str = "company") -> List[Dict]:
        """
        从Tavily获取公司相关资讯
        
        Args:
            company_name: 公司名称
            data_type: 数据类型（company/financing/news）
            
        Returns:
            资讯列表 [{"source": "tavily", ...}]
        """
        queries = {
            "company": f"{company_name} 公司信息 介绍",
            "financing": f"{company_name} 融资 投资",
            "news": f"{company_name} 最新动态 新闻"
        }
        
        results = []
        for query_type, query in queries.items():
            try:
                url = "https://api.tavily.com/search"
                payload = {
                    "api_key": DATA_SOURCES["tavily"]["api_key"],
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 3
                }
                
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("results", []):
                        item["source"] = "tavily"
                        item["source_name"] = "Tavily"
                        item["reliability"] = "medium"
                        item["query_type"] = query_type
                    results.extend(data.get("results", []))
                    logger.info(f"✅ Tavily获取成功: {query_type} ({len(data.get('results', []))} 条)")
            except Exception as e:
                logger.error(f"❌ Tavily异常 ({query_type}): {e}")
        
        return results
    
    def extract_key_data_from_news(self, news_list: List[Dict], company_name: str) -> Dict:
        """
        从新闻资讯中提取关键数据（用于交叉验证）
        
        Args:
            news_list: 新闻列表
            company_name: 公司名称
            
        Returns:
            提取的关键数据 {"field": "value", ...}
        """
        extracted = {
            "source": "tavily",
            "reliability": "medium",
            "valuations_mentioned": [],
            "funding_mentioned": [],
            "team_size_mentioned": []
        }
        
        for news in news_list:
            content = news.get("content", "") + news.get("title", "")
            
            # 简单关键词提取（可扩展为NLP）
            import re
            
            # 估值提取
            valuation_patterns = [
                r"估值[是为]*([\d亿千万零一二三四五六七八九百千万0-9]+)",
                r"估值达([\d亿千万0-9]+)",
                r"([\d亿千万0-9]+)估值"
            ]
            for pattern in valuation_patterns:
                matches = re.findall(pattern, content)
                for m in matches:
                    extracted["valuations_mentioned"].append(m)
            
            # 融资额提取
            funding_patterns = [
                r"融资([\d亿千万0-9]+)",
                r"获得([\d亿千万0-9]+)投资",
                r"轮融资([\d亿千万0-9]+)"
            ]
            for pattern in funding_patterns:
                matches = re.findall(pattern, content)
                for m in matches:
                    extracted["funding_mentioned"].append(m)
        
        return extracted
    
    # =========================================================================
    # 多源交叉验证
    # =========================================================================
    
    def cross_validate(
        self,
        company_name: str,
        base_data: Dict = None
    ) -> Dict:
        """
        多源交叉验证
        
        Args:
            company_name: 公司名称
            base_data: 底稿中的数据（人类提供）
            
        Returns:
            {
                "conflicts": [],           # 冲突列表
                "qcc_data": {...},         # 企查查数据
                "tavily_data": [...],       # Tavily数据
                "extracted_from_news": {...}, # 从新闻提取的关键数据
                "validation_summary": {...}  # 验证摘要
            }
        """
        logger.info(f"\n🔍 开始多源交叉验证: {company_name}")
        
        result = {
            "conflicts": [],
            "qcc_data": None,
            "tavily_data": None,
            "extracted_from_news": None,
            "validation_summary": {}
        }
        
        # ----------------------------------------------------------------
        # 1. 从企查查获取权威工商数据
        # ----------------------------------------------------------------
        logger.info("📊 正在获取企查查工商数据...")
        qcc_result = self.fetch_qcc_data(company_name)
        result["qcc_data"] = qcc_result
        
        # ----------------------------------------------------------------
        # 2. 从Tavily获取新闻资讯
        # ----------------------------------------------------------------
        logger.info("📰 正在获取Tavily新闻资讯...")
        tavily_news = self.fetch_tavily_data(company_name)
        result["tavily_data"] = tavily_news
        
        # 从新闻中提取关键数据
        result["extracted_from_news"] = self.extract_key_data_from_news(tavily_news, company_name)
        
        # ----------------------------------------------------------------
        # 3. 交叉验证分析
        # ----------------------------------------------------------------
        if base_data:
            result["conflicts"] = self._detect_multi_source_conflicts(
                base_data, qcc_result, result["extracted_from_news"]
            )
        
        # 生成验证摘要
        result["validation_summary"] = self._generate_validation_summary(result)
        
        return result
    
    def _detect_multi_source_conflicts(
        self,
        base_data: Dict,
        qcc_data: Dict,
        news_extracted: Dict
    ) -> List[Dict]:
        """
        多源冲突检测
        
        规则：
        1. 多源数据对比
        2. 有冲突 → AI提醒人类
        3. 以人类提供的底稿为准
        """
        conflicts = []
        
        for field in VALIDATION_FIELDS:
            sources_values = {}
            
            # 底稿数据
            if base_data.get(field):
                sources_values["底稿"] = {
                    "value": base_data[field],
                    "reliability": "human"  # 人类数据最高优先级
                }
            
            # 企查查数据
            if qcc_data.get("structured", {}).get(field):
                sources_values["企查查"] = {
                    "value": qcc_data["structured"][field],
                    "reliability": qcc_data.get("reliability", "high")
                }
            
            # 新闻提取数据
            if field == "valuation" and news_extracted.get("valuations_mentioned"):
                # 取众数或最新值（简化处理）
                vals = news_extracted["valuations_mentioned"]
                sources_values["新闻"] = {
                    "value": vals[0] if vals else None,
                    "reliability": "low"  # 新闻提取可靠性较低
                }
            
            if field == "funding_amount" and news_extracted.get("funding_mentioned"):
                vals = news_extracted["funding_mentioned"]
                sources_values["新闻"] = {
                    "value": vals[0] if vals else None,
                    "reliability": "low"
                }
            
            # 检测冲突
            if len(sources_values) >= 2:
                unique_values = set(str(v["value"]) for v in sources_values.values() if v["value"])
                
                if len(unique_values) > 1:
                    # 有冲突！
                    conflict = {
                        "field": field,
                        "field_name": field.replace("_", " ").title(),
                        "sources": sources_values,
                        "base_value": base_data.get(field),  # 人类底稿数据
                        "ai_recommendation": self._resolve_conflict(sources_values),
                        "resolution": "pending_human"  # 待人类确认
                    }
                    conflicts.append(conflict)
                    logger.warning(f"⚠️ 冲突检测: {field}")
        
        return conflicts
    
    def _resolve_conflict(self, sources_values: Dict) -> str:
        """
        AI建议冲突解决（但不作为最终结论）
        
        规则：
        1. 人类数据优先
        2. 高可靠性数据优先
        3. 返回AI建议，但人类决定
        """
        # 按可靠性排序
        reliability_order = {"human": 3, "high": 2, "medium": 1, "low": 0}
        
        sorted_sources = sorted(
            sources_values.items(),
            key=lambda x: reliability_order.get(x[1]["reliability"], 0),
            reverse=True
        )
        
        # AI建议取最高可靠性的数据
        ai_recommended = sorted_sources[0]
        
        # 如果人类数据不是最高的，发出提醒
        if ai_recommended[0] != "底稿" and "底稿" in sources_values:
            return f"AI建议: 以{ai_recommended[0]}数据({ai_recommended[1]['value']})为准，但人类底稿数据({sources_values['底稿']['value']})可能更准确，请人类确认。"
        else:
            return f"AI建议: 以{ai_recommended[0]}数据({ai_recommended[1]['value']})为准。"
    
    def _generate_validation_summary(self, validation_result: Dict) -> Dict:
        """生成验证摘要"""
        return {
            "qcc_available": validation_result["qcc_data"] and not validation_result["qcc_data"].get("error"),
            "tavily_news_count": len(validation_result["tavily_data"]) if validation_result["tavily_data"] else 0,
            "conflict_count": len(validation_result["conflicts"]),
            "has_conflicts": len(validation_result["conflicts"]) > 0
        }
    
    # =========================================================================
    # 补充信息写入共享库
    # =========================================================================
    
    def write_to_shared(self, project_tag: str, content: str, content_type: str, metadata: Dict):
        """
        将补充信息写入共享库
        
        Args:
            project_tag: 项目标签
            content: 内容文本
            content_type: 内容类型（qcc_news/supplement/conflict_alert）
            metadata: 元数据
        """
        # 向量化
        vectors = self._get_embeddings([content])
        if not vectors:
            logger.error("❌ 向量化失败，跳过写入")
            return False
        
        # 构造元数据
        meta = {
            "type": content_type,  # qcc/news/supplement/conflict
            "project_tag": project_tag,
            "source": "secretary_auto",  # 来源：秘书自动
            "round": 0,  # 补充信息轮次为0
            "ingest_time": datetime.now().isoformat(),
            "content_preview": content[:200],
            **metadata
        }
        
        # 写入Milvus
        try:
            self.collection.insert([
                vectors,
                [project_tag],
                [json.dumps(meta, ensure_ascii=False)]
            ])
            self.collection.flush()
            logger.info(f"✅ 写入共享库成功: {content_type}")
            return True
        except Exception as e:
            logger.error(f"❌ 写入失败: {e}")
            return False
    
    # =========================================================================
    # 主流程
    # =========================================================================
    
    def supplement(
        self,
        project_tag: str,
        company_name: str,
        base_data: Dict = None,  # 底稿中的人类数据
        enable_qcc: bool = True,
        enable_tavily: bool = True
    ):
        """
        执行情报补充主流程
        
        Args:
            project_tag: 项目标签
            company_name: 公司名称
            base_data: 底稿中的关键数据（用于交叉验证）
            enable_qcc: 是否启用企查查
            enable_tavily: 是否启用Tavily
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"📥 秘书情报补充 - {project_tag}")
        logger.info(f"{'=' * 60}")
        logger.info(f"   公司: {company_name}")
        logger.info(f"   企查查: {'启用' if enable_qcc else '禁用'}")
        logger.info(f"   Tavily: {'启用' if enable_tavily else '禁用'}")
        logger.info(f"{'=' * 60}\n")
        
        all_supplements = []
        conflicts = []
        
        # ----------------------------------------------------------------
        # 1. 多源交叉验证
        # ----------------------------------------------------------------
        if enable_qcc or enable_tavily:
            validation_result = self.cross_validate(company_name, base_data)
            conflicts = validation_result.get("conflicts", [])
            
            # ----------------------------------------------------------------
            # 2. 展示验证结果
            # ----------------------------------------------------------------
            print("\n" + "=" * 60)
            print("🔍 多源交叉验证结果")
            print("=" * 60)
            
            # 企查查数据
            if validation_result["qcc_data"] and not validation_result["qcc_data"].get("error"):
                qcc = validation_result["qcc_data"]
                print(f"\n📊 企查查数据 (可信度: {qcc['reliability']})")
                structured = qcc.get("structured", {})
                for k, v in structured.items():
                    print(f"   {k}: {v}")
            else:
                print(f"\n📊 企查查数据: 获取失败")
            
            # 新闻资讯
            tavily_count = len(validation_result["tavily_data"]) if validation_result["tavily_data"] else 0
            print(f"\n📰 新闻资讯: 获取到 {tavily_count} 条")
            
            # 冲突检测
            print(f"\n⚠️  冲突检测: {len(conflicts)} 个")
            
            # ----------------------------------------------------------------
            # 3. 冲突展示与人类确认
            # ----------------------------------------------------------------
            if conflicts:
                print("\n" + "-" * 60)
                print("🚨 冲突详情（以人类底稿为准，AI提醒：）")
                print("-" * 60)
                
                for i, conflict in enumerate(conflicts, 1):
                    print(f"\n冲突 {i}: {conflict.get('field_name', conflict.get('field'))}")
                    
                    for source, info in conflict.get("sources", {}).items():
                        marker = " 👈 人类数据" if source == "底稿" else ""
                        marker += " ⭐ AI推荐" if "AI建议" in conflict.get("ai_recommendation", "") and source in conflict["ai_recommendation"] else ""
                        print(f"   {source}: {info.get('value')} (可信度: {info.get('reliability')}){marker}")
                    
                    print(f"\n   💡 {conflict.get('ai_recommendation', '')}")
                
                print("\n" + "-" * 60)
                print("📌 规则: 有冲突的数据以人类底稿为准")
                print("   人类可更新底稿后重新触发本流程")
                print("-" * 60)
                
                # 询问是否继续
                print("\n请选择操作：")
                print("  [Y] 确认，继续执行情报补充")
                print("  [N] 暂停，先更新底稿")
                print("-" * 60)
                
                while True:
                    choice = input("\n👉 请输入选择 (Y/N): ").strip().upper()
                    
                    if choice == 'Y':
                        print("\n✅ 确认，继续执行情报补充...")
                        
                        # 写入确认记录
                        self.write_to_shared(
                            project_tag=project_tag,
                            content=json.dumps({
                                "action": "conflict_confirmed",
                                "confirmed_at": datetime.now().isoformat(),
                                "conflicts_count": len(conflicts),
                                "ai_recommendation": "以人类底稿为准"
                            }, ensure_ascii=False),
                            content_type="human_confirm",
                            metadata={
                                "action": "conflict_acknowledged",
                                "confirmed_at": datetime.now().isoformat(),
                                "conflicts_count": len(conflicts)
                            }
                        )
                        break
                        
                    elif choice == 'N':
                        print("\n⏸️ 已暂停，请先更新底稿后再重新触发...")
                        
                        self.write_to_shared(
                            project_tag=project_tag,
                            content=json.dumps({
                                "action": "paused_for_base_update",
                                "paused_at": datetime.now().isoformat(),
                                "conflicts_count": len(conflicts),
                                "message": "人类选择暂停，需更新底稿后重新触发"
                            }, ensure_ascii=False),
                            content_type="process_paused",
                            metadata={
                                "action": "paused",
                                "paused_at": datetime.now().isoformat(),
                                "reason": "conflict_needs_base_update"
                            }
                        )
                        
                        connections.disconnect("default")
                        return
                    
                    else:
                        print("⚠️ 无效选择，请重新输入 (Y/N)")
            else:
                print("\n✅ 未检测到冲突，继续执行...")
            
            # ----------------------------------------------------------------
            # 4. 写入企查查数据到共享库
            # ----------------------------------------------------------------
            if enable_qcc and validation_result["qcc_data"] and not validation_result["qcc_data"].get("error"):
                supplement_text = self._format_qcc_data(validation_result["qcc_data"]["raw_data"])
                all_supplements.append(supplement_text)
                
                self.write_to_shared(
                    project_tag=project_tag,
                    content=supplement_text,
                    content_type="qcc_supplement",
                    metadata={
                        "data_source": "qcc",
                        "company_name": company_name,
                        "reliability": validation_result["qcc_data"].get("reliability", "high")
                    }
                )
            
            # ----------------------------------------------------------------
            # 5. 写入Tavily新闻到共享库
            # ----------------------------------------------------------------
            if enable_tavily and validation_result["tavily_data"]:
                for news in validation_result["tavily_data"]:
                    title = news.get("title", "")
                    content = news.get("content", "")
                    url = news.get("url", "")
                    
                    if title:
                        news_text = f"【{title}】\n{content}\n来源: {url}"
                        all_supplements.append(news_text)
                        
                        self.write_to_shared(
                            project_tag=project_tag,
                            content=news_text,
                            content_type="news_supplement",
                            metadata={
                                "data_source": "tavily",
                                "news_title": title,
                                "news_url": url,
                                "company_name": company_name,
                                "reliability": "medium"
                            }
                        )
        
        # ----------------------------------------------------------------
        # 6. 完成
        # ----------------------------------------------------------------
        logger.info(f"\n✨ 情报补充完成!")
        logger.info(f"   补充条目: {len(all_supplements)}")
        logger.info(f"   冲突数量: {len(conflicts)}")
        logger.info(f"   共享库实体数: {self.collection.num_entities}")
        
        connections.disconnect("default")
    
    def _format_qcc_data(self, data: Dict) -> str:
        """格式化企查查数据为可读文本"""
        lines = ["【企查查工商信息】"]
        
        # 基础信息
        if data.get("Name"):
            lines.append(f"公司名称: {data.get('Name')}")
        if data.get("LegalRepresentative"):
            lines.append(f"法定代表人: {data.get('LegalRepresentative')}")
        if data.get("EstiblishTime"):
            lines.append(f"成立日期: {data.get('EstiblishTime')}")
        if data.get("Capital"):
            lines.append(f"注册资本: {data.get('Capital')}")
        if data.get("Status"):
            lines.append(f"经营状态: {data.get('Status')}")
        
        # 股东信息
        if data.get("Partners"):
            lines.append(f"\n主要股东:")
            for p in data.get("Partners", [])[:5]:
                lines.append(f"  - {p.get('Name')}: {p.get('Percent', 'N/A')}%")
        
        # 融资历史（如有）
        if data.get("Financing"):
            lines.append(f"\n融资历史:")
            for f in data.get("Financing", [])[:3]:
                lines.append(f"  - {f.get('Round')}: {f.get('Amount', 'N/A')}")
        
        return "\n".join(lines)

# ============================================================================
# 交互入口
# ============================================================================

def main():
    """人类交互式入口"""
    
    print("\n" + "=" * 60)
    print("📥 Sovereign-IQ | 秘书情报补充技能 v2.0")
    print("=" * 60)
    print("\n💡 使用说明:")
    print("   1. 底稿已入库后运行本脚本")
    print("   2. 输入底稿中的关键数据（用于交叉验证）")
    print("   3. 脚本从企查查/Tavily抓取多源数据")
    print("   4. 检测冲突时以人类底稿为准，AI提醒人类")
    print()
    
    # 输入项目标签
    project_tag = input("🏷️ 请输入项目标签 (如 YUSHU_2026): ").strip()
    
    if not project_tag:
        print("❌ project_tag 不能为空")
        return
    
    # 输入公司名称
    company_name = input("🏢 请输入公司名称: ").strip()
    
    if not company_name:
        print("❌ 公司名称不能为空")
        return
    
    # ----------------------------------------------------------------
    # 输入底稿关键数据（用于交叉验证）
    # ----------------------------------------------------------------
    print("\n" + "-" * 60)
    print("📋 请输入底稿中的关键数据（用于多源交叉验证）")
    print("   如无某项数据，可直接回车跳过")
    print("-" * 60)
    
    base_data = {}
    
    base_data["company_name"] = input("   公司名称: ").strip() or None
    base_data["valuation"] = input("   估值 (如: 100亿): ").strip() or None
    base_data["funding_amount"] = input("   融资金额 (如: 10亿): ").strip() or None
    base_data["team_size"] = input("   团队规模 (如: 100人): ").strip() or None
    base_data["established_date"] = input("   成立日期 (如: 2020-01-01): ").strip() or None
    base_data["revenue"] = input("   营收 (如: 5亿): ").strip() or None
    
    # 清理None值
    base_data = {k: v for k, v in base_data.items() if v}
    
    if base_data:
        print(f"\n📝 已录入底稿数据: {list(base_data.keys())}")
    else:
        print("\n⚠️ 未录入底稿数据，将仅进行多源数据抓取")
    
    # 选择数据源
    enable_qcc = input("\n📊 是否启用企查查? (Y/n): ").strip().lower() != 'n'
    enable_tavily = input("📰 是否启用Tavily? (Y/n): ").strip().lower() != 'n'
    
    print("\n" + "-" * 60)
    
    # 执行补充
    supplement = SecretarySupplement()
    supplement.supplement(
        project_tag=project_tag,
        company_name=company_name,
        base_data=base_data if base_data else None,
        enable_qcc=enable_qcc,
        enable_tavily=enable_tavily
    )


if __name__ == "__main__":
    main()
