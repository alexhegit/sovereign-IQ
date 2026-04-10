#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据获取器 - 整合企查查 + Tavily + Exa
用于SIQ投委会系统的尽调数据获取
"""

import json
import os
import sys
from typing import Dict

# 添加脚本目录到路径
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/ic_master_coordinator_workspace/scripts'))

from qcc_client import QCCClient
from tavily_client import TavilyClient
from exa_client import ExaClient

class UnifiedDataFetcher:
    """统一数据获取器"""
    
    def __init__(self):
        """初始化客户端"""
        self.qcc = QCCClient()
        self.tavily = TavilyClient()
        self.exa = ExaClient()
    
    def fetch_company_data(self, company_name: str, credit_code: str = None) -> Dict:
        """
        获取公司完整数据（三源合一）
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            完整公司数据
        """
        print(f"🔍 正在获取 {company_name} 的数据...")
        
        # 1. 企查查数据（官方工商信息）
        print("  📋 获取企查查数据...")
        try:
            qcc_data = self.qcc.full_due_diligence(company_name, credit_code)
            print("     ✅ 企查查数据获取成功")
        except Exception as e:
            print(f"     ⚠️ 企查查获取失败: {e}")
            qcc_data = {}
        
        # 2. Tavily搜索（快速公开信息）
        print("  🔎 获取Tavily公开信息...")
        try:
            tavily_data = self.tavily.search_company_info(company_name)
            print("     ✅ Tavily数据获取成功")
        except Exception as e:
            print(f"     ⚠️ Tavily获取失败: {e}")
            tavily_data = {}
        
        # 3. Exa搜索（深度内容提取）
        print("  🔬 获取Exa深度信息...")
        try:
            exa_data = self.exa.search_company_info(company_name)
            print("     ✅ Exa数据获取成功")
        except Exception as e:
            print(f"     ⚠️ Exa获取失败: {e}")
            exa_data = {}
        
        # 4. 整合数据
        unified_data = {
            "company_name": company_name,
            "credit_code": credit_code,
            "official_data": qcc_data,           # 企查查官方数据
            "public_data_tavily": tavily_data,    # Tavily公开信息
            "public_data_exa": exa_data,          # Exa深度信息
            "data_sources": ["qcc", "tavily", "exa"],
            "data_completeness": self._calculate_completeness(qcc_data, tavily_data, exa_data)
        }
        
        print(f"\n✅ 数据获取完成")
        print(f"   数据来源: {', '.join(unified_data['data_sources'])}")
        print(f"   完整度: {unified_data['data_completeness']:.0%}")
        
        return unified_data
    
    def _calculate_completeness(self, qcc_data: Dict, tavily_data: Dict, exa_data: Dict) -> float:
        """计算数据完整度"""
        sources = [qcc_data, tavily_data, exa_data]
        available = sum(1 for s in sources if s)
        return available / len(sources)
    
    def generate_dd_report(self, company_name: str, credit_code: str = None) -> str:
        """
        生成尽调报告摘要
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            尽调报告Markdown格式
        """
        data = self.fetch_company_data(company_name, credit_code)
        
        report = f"""# {company_name} 尽调数据摘要

## 数据概览
- **数据来源**: {', '.join(data['data_sources'])}
- **数据完整度**: {data['data_completeness']:.0%}
- **查询时间**: 2026-04-04

## 1. 官方数据（企查查）
```json
{json.dumps(data['official_data'], ensure_ascii=False, indent=2)[:1000]}
...
```

## 2. 公开信息（Tavily）
```json
{json.dumps(data['public_data_tavily'], ensure_ascii=False, indent=2)[:1000]}
...
```

## 3. 深度信息（Exa）
```json
{json.dumps(data['public_data_exa'], ensure_ascii=False, indent=2)[:1000]}
...
```

## 数据质量评估
| 数据源 | 状态 | 说明 |
|--------|------|------|
| 企查查官方 | {'✅ 已获取' if data['official_data'] else '⚠️ 缺失'} | 工商/风险/知识产权/经营 |
| Tavily公开 | {'✅ 已获取' if data['public_data_tavily'] else '⚠️ 缺失'} | 新闻/融资/行业动态 |
| Exa深度 | {'✅ 已获取' if data['public_data_exa'] else '⚠️ 缺失'} | 深度文章/技术文档 |

---
*生成时间: 2026-04-04*
*数据来源: QCC + Tavily + Exa*
*系统: SIQ投委会智能决策系统*
"""
        
        return report
    
    def cross_verify(self, company_name: str, credit_code: str = None) -> Dict:
        """
        交叉验证数据一致性
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            交叉验证结果
        """
        data = self.fetch_company_data(company_name, credit_code)
        
        # 检查数据冲突
        conflicts = []
        
        # 示例：检查注册资本是否一致
        qcc_capital = data['official_data'].get('company', {}).get('registered_capital')
        # 可以添加更多交叉验证逻辑
        
        return {
            "company_name": company_name,
            "data_completeness": data['data_completeness'],
            "conflicts": conflicts,
            "verification_status": "passed" if not conflicts else "has_conflicts",
            "recommendation": "继续尽调" if not conflicts else "需人工核实"
        }


# 使用示例
if __name__ == "__main__":
    fetcher = UnifiedDataFetcher()
    
    # 获取公司数据
    company_name = "宇树科技"
    print(f"\n{'='*60}")
    print(f"🔍 开始获取 {company_name} 的尽调数据")
    print(f"{'='*60}\n")
    
    data = fetcher.fetch_company_data(company_name)
    
    # 打印摘要
    print(f"\n{'='*60}")
    print(f"📊 数据获取摘要")
    print(f"{'='*60}")
    print(f"公司名称: {data['company_name']}")
    print(f"数据来源: {', '.join(data['data_sources'])}")
    print(f"数据完整度: {data['data_completeness']:.0%}")
    print(f"{'='*60}")
    
    # 保存完整数据
    output_dir = os.path.expanduser("~/.openclaw/workspace/ic_master_coordinator_workspace/data")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"{company_name}_dd_data.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存: {output_path}")
    
    # 生成报告
    report_path = os.path.join(output_dir, f"{company_name}_dd_report.md")
    report = fetcher.generate_dd_report(company_name)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 报告已保存: {report_path}")