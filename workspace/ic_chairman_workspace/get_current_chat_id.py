#!/usr/bin/env python3
"""
获取当前对话的飞书群 ID
"""

import json
import os
import requests

def load_lark_config():
    """加载飞书配置"""
    with open('lark_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_tenant_access_token(app_id, app_secret):
    """获取飞书租户访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 0:
            return data.get("tenant_access_token")
        else:
            raise Exception(f"获取 Token 失败：{data.get('msg')}")
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

def get_user_chats(token):
    """获取用户所在的所有群聊"""
    url = "https://open.feishu.cn/open-apis/chat/list_v2"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"API Response Status: {response.status_code}")
        print(f"API Response Body: {response.text[:200]}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("chats", [])
            else:
                raise Exception(f"获取群聊列表失败：{data.get('msg')}")
        else:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    """主函数"""
    print("=" * 70)
    print("  获取飞书群 ID")
    print("=" * 70)
    print()
    
    # 加载配置
    try:
        config = load_lark_config()
    except Exception as e:
        print(f"❌ 加载配置失败：{e}")
        return
    
    app_id = config.get('lark_config', {}).get('app_id')
    app_secret = config.get('lark_config', {}).get('app_secret')
    
    # 获取 Token
    try:
        token = get_tenant_access_token(app_id, app_secret)
        print(f"✅ 已获取飞书访问令牌 (长度：{len(token)})")
    except Exception as e:
        print(f"❌ 获取 Token 失败：{e}")
        return
    
    # 获取用户所在群聊
    print("\n📋 获取用户所在群聊列表...")
    chats = get_user_chats(token)
    
    if not chats:
        print("❌ 未获取到群聊列表")
        print("\n可能的原因:")
        print("1. 飞书应用缺少 '获取群聊列表' 权限")
        print("2. 当前用户不是任何群聊的成员")
        print("3. API URL 可能不正确")
        return
    
    print(f"\n✅ 成功获取 {len(chats)} 个群聊")
    print()
    print("📱 您所在的群聊:")
    print("-" * 70)
    
    for i, chat in enumerate(chats, 1):
        chat_id = chat.get('chat_id', 'Unknown')
        name = chat.get('name', 'Unknown')
        chat_type = chat.get('chat_type', 'Unknown')
        print(f"{i:2}. {name:35} | {chat_id:40} | {chat_type}")
    
    print("-" * 70)
    
    # 自动选择 SIQ 相关群聊
    siq_chats = [chat for chat in chats if 'SIQ' in chat.get('name', '') or '投委' in chat.get('name', '')]
    
    if siq_chats:
        print(f"\n✅ 找到 SIQ 相关群聊 ({len(siq_chats)} 个):")
        for i, chat in enumerate(siq_chats, 1):
            chat_id = chat.get('chat_id', 'Unknown')
            name = chat.get('name', 'Unknown')
            print(f"  {i}. {name} ({chat_id})")
        
        # 自动选择第一个 SIQ 群聊
        target_chat = siq_chats[0]
        chat_id = target_chat['chat_id']
        print(f"\n🎯 自动选择：{target_chat['name']}")
        print(f"   Chat ID: {chat_id}")
        
        # 保存到配置文件
        config['lark_config']['chat_id'] = chat_id
        config['chat_id_last_updated'] = "2026-04-06T17:17:00Z"
        
        try:
            with open('lark_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print("\n✅ 群 ID 已保存到配置")
        except Exception as e:
            print(f"❌ 保存失败：{e}")
            
        print("\n" + "=" * 70)
        print("现在可以发送自我介绍到 SIQ 群聊!")
        print("=" * 70)
        print()
        
        # 返回选中的群 ID
        return chat_id
    else:
        print("\n⚠️  未找到 SIQ 相关群聊")
        print("   请手动选择一个群聊")
        
        # 返回第一个群聊 ID 作为默认
        if chats:
            chat_id = chats[0]['chat_id']
            print(f"使用第一个群聊：{chats[0]['name']}")
            print(f"   Chat ID: {chat_id}")
            return chat_id
        
        return None

if __name__ == "__main__":
    chat_id = main()
    
    if chat_id:
        print("\n当前群聊 ID 配置:")
        print(f"  {chat_id}")
    else:
        print("\n未成功获取群聊 ID")
