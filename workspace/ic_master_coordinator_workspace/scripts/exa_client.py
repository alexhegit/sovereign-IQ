#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exa API客户端 - 用于SIQ投委会系统
支持深度网页搜索和内容提取
"""

import os
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.expanduser("~/.openclaw/workspace/ic_master_coordinator_workspace/config/.env"))

class ExaClient:
    """Exa搜索API客户端"""
    
    BASE_URL = "https://api.exa.ai"
    
    def __init__(self, api_key: str = None):
        """初始化客户端"""
        if api_key is None:
            api_key = os.getenv("EXA_API_KEY")
        
        if not api_key:
            raise ValueError("EXA_API_KEY not found. Please set it in environment variables.")
        
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def search(self, 
               query: str, 
               num_results: int = 10,
               include_domains: List[str] = None,
               exclude_domains: List[str] = None,
               start_published_date: str = None,
               end_published_date: str = None) -> Dict:
        """
        执行搜索
        
        Args:
            query: 搜索查询（支持自然语言）
            num_results: 结果数量
            include_domains: 包含的域名列表
            exclude_domains: 排除的域名列表
            start_published_date: 开始日期 (YYYY-MM-DD)
            end_published_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            搜索结果
        """
        payload = {
            "query": query,
            "numResults": num_results,
            "contents": {
                "text": True,
                "highlights": True
            }
        }
        
        if include_domains:
            payload["includeDomains"] = include_domains
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains
        if start_published_date:
            payload["startPublishedDate"] = start_published_date
        if end_published_date:
            payload["endPublishedDate"] = end_published_date
        
        response = requests.post(
            f"{self.BASE_URL}/search",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    def search_company_info(self, company_name: str) -> Dict:
        """
        搜索公司信息（专门用于投研）
        
        Args:
            company_name: 公司名称
        
        Returns:
            公司相关信息
        """
        # 使用自然语言查询
        query = f"{company_name} 公司介绍 融资 估值 投资方 商业模式 竞争对手"
        
        return self.search(
            query=query,
            num_results=10,
            start_published_date="2023-01-01"  # 近两年信息
        )
    
    def search_industry_info(self, industry: str) -> Dict:
        """
        搜索行业信息
        
        Args:
            industry: 行业名称
        
        Returns:
            行业相关信息
        """
        query = f"{industry} 行业分析 市场规模 发展趋势 主要玩家"
        
        return self.search(
            query=query,
            num_results=8
        )
    
    def search_competitors(self, company_name: str) -> Dict:
        """
        搜索竞争对手信息
        
        Args:
            company_name: 公司名称
        
        Returns:
            竞争对手相关信息
        """
        query = f"{company_name} 竞争对手 comparison vs"
        
        return self.search(
            query=query,
            num_results=8
        )
    
    def extract_content(self, url: str) -> Dict:
        """
        提取网页内容
        
        Args:
            url: 网页URL
        
        Returns:
            提取的内容
        """
        payload = {
            "urls": [url],
            "text": True,
            "highlights": True
        }
        
        response = requests.post(
            f"{self.BASE_URL}/contents",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    def find_similar(self, url: str, num_results: int = 5) -> Dict:
        """
        查找相似内容
        
        Args:
            url: 参考网页URL
            num_results: 结果数量
        
        Returns:
            相似内容
        """
        payload = {
            "url": url,
            "numResults": num_results,
            "contents": {
                "text": True
            }
        }
        
        response = requests.post(
            f"{self.BASE_URL}/findSimilar",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()


# 使用示例
if __name__ == "__main__":
    client = ExaClient()
    
    # 测试搜索公司信息
    print("🔍 测试搜索公司信息...")
    result = client.search_company_info("宇树科技")
    
    print(f"\n✅ 搜索完成")
    print(f"结果数量: {len(result.get('results', []))}")
    
    # 打印第一个结果
    if result.get('results'):
        first = result['results'][0]
        print(f"\n第一条结果:")
        print(f"标题: {first.get('title', 'N/A')}")
        print(f"URL: {first.get('url', 'N/A')}")
        print(f"摘要: {first.get('text', 'N/A')[:200]}...")