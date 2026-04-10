#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企查查API客户端 - 用于SIQ投委会系统
支持MCP协议：company, risk, ipr, operation 四类查询
"""

import json
import requests
from typing import Dict, Optional

class QCCClient:
    """企查查API客户端 - MCP协议"""
    
    def __init__(self, config_path: str = None):
        """初始化客户端"""
        if config_path is None:
            config_path = "~/.openclaw/workspace/ic_master_coordinator_workspace/config/qcc_mcp_config.json"
        
        import os
        config_path = os.path.expanduser(config_path)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.servers = config['mcpServers']
        self.session = requests.Session()
    
    def _call_mcp(self, server_key: str, tool_name: str, params: Dict) -> Dict:
        """
        调用MCP端点的tools/call方法
        
        Args:
            server_key: 服务器配置键（如 'qcc-company'）
            tool_name: 工具名称（如 'get_company_registration_info'）
            params: 参数字典
        
        Returns:
            API响应结果
        """
        server = self.servers[server_key]
        
        # 构建请求头 - 必须包含 Accept: application/json, text/event-stream
        headers = {
            **server.get('headers', {}),
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
        
        # JSON-RPC 2.0 格式 - 使用 tools/call 方法
        payload = {
            'jsonrpc': '2.0',
            'method': 'tools/call',
            'params': {
                'name': tool_name,
                'arguments': params
            },
            'id': 1
        }
        
        response = self.session.post(
            server['url'],
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # 解析SSE格式响应
        result = None
        error = None
        for line in response.text.strip().split('\n'):
            if line.startswith('data:'):
                data = json.loads(line[5:])
                if 'error' in data:
                    error = data['error']
                elif 'result' in data:
                    result = data['result']
        
        if error:
            raise Exception(f"QCC API Error: {error.get('message', 'Unknown error')}")
        
        # 解析content中的JSON字符串
        if result and 'content' in result:
            content_list = result['content']
            if content_list and isinstance(content_list, list):
                text = content_list[0].get('text', '{}')
                try:
                    return json.loads(text)
                except:
                    return {'raw_text': text}
        
        return result or {}
    
    def query_company(self, company_name: str, credit_code: str = None) -> Dict:
        """
        查询企业工商信息
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            企业工商信息
        """
        params = {"searchKey": company_name}
        
        return self._call_mcp('qcc-company', 'get_company_registration_info', params)
    
    def query_company_profile(self, company_name: str, credit_code: str = None) -> Dict:
        """
        查询企业简介
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            企业简介信息
        """
        params = {"searchKey": company_name}
        
        return self._call_mcp('qcc-company', 'get_company_profile', params)
    
    def query_shareholder(self, company_name: str, credit_code: str = None) -> Dict:
        """
        查询股东信息
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            股东信息
        """
        params = {"searchKey": company_name}
        
        return self._call_mcp('qcc-company', 'get_shareholder_info', params)
    
    def query_key_personnel(self, company_name: str, credit_code: str = None) -> Dict:
        """
        查询主要人员
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            主要人员信息
        """
        params = {"searchKey": company_name}
        
        return self._call_mcp('qcc-company', 'get_key_personnel', params)
    
    def query_risk(self, company_name: str, credit_code: str = None) -> Dict:
        """
        查询企业风险信息（经营异常、失信、严重违法等）
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            风险信息
        """
        params = {"searchKey": company_name}
        
        # risk端点使用相同的方法名
        return self._call_mcp('qcc-risk', 'get_company_registration_info', params)
    
    def query_ipr(self, company_name: str, credit_code: str = None) -> Dict:
        """
        查询企业知识产权（专利、商标、软著等）
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            知识产权信息
        """
        params = {"searchKey": company_name}
        
        # ipr端点使用相同的方法查询
        return self._call_mcp('qcc-ipr', 'get_company_registration_info', params)
    
    def query_operation(self, company_name: str, credit_code: str = None) -> Dict:
        """
        查询企业经营信息（上市情况、对外投资等）
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            经营信息
        """
        params = {"searchKey": company_name}
        
        return self._call_mcp('qcc-operation', 'get_listing_info', params)
    
    def full_due_diligence(self, company_name: str, credit_code: str = None) -> Dict:
        """
        完整尽调 - 调用所有端点
        
        Args:
            company_name: 公司名称
            credit_code: 统一社会信用代码（可选）
        
        Returns:
            完整尽调报告
        """
        return {
            "company": self.query_company(company_name, credit_code),
            "company_profile": self.query_company_profile(company_name, credit_code),
            "shareholder": self.query_shareholder(company_name, credit_code),
            "key_personnel": self.query_key_personnel(company_name, credit_code),
            "risk": self.query_risk(company_name, credit_code),
            "ipr": self.query_ipr(company_name, credit_code),
            "operation": self.query_operation(company_name, credit_code)
        }


# 使用示例
if __name__ == "__main__":
    client = QCCClient()
    
    # 测试查询
    result = client.full_due_diligence("宇树科技")
    print(json.dumps(result, ensure_ascii=False, indent=2))