#!/usr/bin/env python3
"""
飞书 (Lark) 连接验证脚本
验证 SIQ 投委会主席的飞书账号配置
"""

import json
import requests
from datetime import datetime

def load_config():
    """加载飞书配置"""
    try:
        with open('lark_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def verify_app_id_secret(app_id, app_secret):
    """验证飞书应用的 App ID 和 App Secret"""
    # 飞书开放平台获取 token 接口
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    
    try:
        response = requests.post(token_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                token = data.get("tenant_access_token")
                print(f"\n✅ 飞书应用验证成功!")
                print(f"   Token 已获取 (长度：{len(token)})")
                return True
            else:
                print(f"\n❌ 获取 Token 失败：{data.get('msg')}")
                return False
        else:
            print(f"\n❌ HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ 验证失败：{e}")
        return False

def main():
    """主函数"""
    print("=" * 70)
    print("  SIQ 投委会主席 - 飞书账号配置验证")
    print("=" * 70)
    print()
    
    # 加载配置
    config = load_config()
    if not config:
        print("❌ 配置文件 lark_config.json 不存在")
        return
    
    # 显示配置信息
    print(f"📱 Agent ID: {config.get('agent_id')}")
    print(f"👤 Agent Name: {config.get('agent_name')}")
    print()
    print(f"🔑 飞书配置:")
    print(f"   App ID: {config.get('lark_config', {}).get('app_id')}")
    print(f"   App Secret: {'*' * len(config.get('lark_config', {}).get('app_secret', ''))}")
    print(f"   状态：{config.get('status')}")
    print()
    
    # 验证配置
    app_id = config.get('lark_config', {}).get('app_id')
    app_secret = config.get('lark_config', {}).get('app_secret')
    
    if app_id and app_secret:
        verify_app_id_secret(app_id, app_secret)
    else:
        print("⚠️  App ID 或 App Secret 为空")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
