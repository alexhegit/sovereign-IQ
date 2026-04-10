#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tavily搜索API客户端 - 用于SIQ投委会系统
支持中英文搜索，速度快，结果准确
"""

import os
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.expanduser("~/.openclaw/workspace/ic_master_coordinator_workspace/config/.env"))

class TavilyClient:
    """Tavily搜索API客户端"""
    
    BASE_URL = "https://api.tavily.com"
    
    def __init__(self, api_key: str = None):
        """初始化客户端"""
        if api_key is None:
            api_key = os.getenv("TAVILY_API_KEY")
        
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found. Please set it in environment variables.")
        
        self.api_key = api_key
    
    def search(self, 
               query: str, 
               search_depth: str = "advanced",
               include_domains: List[str] = None,
               exclude_domains: List[str] = None,
               max_results: int = 10) -> Dict:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            search_depth: 搜索深度 (basic/advanced)
            include_domains: 包含的域名列表
            exclude_domains: 排除的域名列表
            max_results: 最大结果数
        
        Returns:
            搜索结果
        """
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results
        }
        
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        
        response = requests.post(
            f"{self.BASE_URL}/search",
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    def search_company_info(self, company_name: str, industry: str = None) -> Dict:
        """
        搜索公司信息（专门用于投研）
        
        Args:
            company_name: 公司名称
            industry: 行业（可选）
        
        Returns:
            公司相关信息
        """
        query = f"{company_name} 融资 估值 投资"
        if industry:
            query += f" {industry}"
        
        return self.search(
            query=query,
            search_depth="advanced",
            max_results=15
        )
    
    def search_industry_info(self, industry: str) -> Dict:
        """
        搜索行业信息
        
        Args:
            industry: 行业名称
        
        Returns:
            行业相关信息
        """
        query = f"{industry} 市场规模 竞争格局 发展趋势"
        
        return self.search(
            query=query,
            search_depth="advanced",
            max_results=10
        )
    
    def search_competitors(self, company_name: str) -> Dict:
        """
        搜索竞争对手信息
        
        Args:
            company_name: 公司名称
        
        Returns:
            竞争对手相关信息
        """
        query = f"{company_name} 竞品 竞争对手 对比"
        
        return self.search(
            query=query,
            search_depth="advanced",
            max_results=10
        )


# 使用示例
if __name__ == "__main__":
    client = TavilyClient()
    
    # 测试搜索公司信息
    result = client.search_company_info("宇树科技", "机器人")
    print(json.dumps(result, ensure_ascii=False, indent=2))