#!/usr/bin/env python3
"""
获取飞书群 ID 脚本
通过飞书 API 获取当前群聊 ID
"""

import json
import requests
from datetime import datetime

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

def get_group_chat_id(token):
    """获取群聊 ID"""
    # 方法 1: 从消息历史中获取（如果您已发送过消息）
    # 方法 2: 手动输入
    
    print("\n请选择获取群 ID 的方式：")
    print("1. 手动输入群 ID (如果您知道)")
    print("2. 获取当前对话的群 ID (推荐)")
    
    choice = input("\n请输入选项 (1 或 2): ").strip()
    
    if choice == "1":
        chat_id = input("请输入飞书群 ID (以 chat_ 开头): ").strip()
        return chat_id
    elif choice == "2":
        # 尝试获取当前对话的群 ID
        # 这里需要您提供对话 ID 或通过其他方式获取
        print("\n⚠️  需要您提供对话 ID 或通过飞书后台获取")
        print("   请查看飞书客户端 → 群聊详情 → 复制群 ID")
        print("   或者通过飞书开放平台获取")
        return None
    else:
        print("❌ 无效选项")
        return None

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
        print(f"✅ 已获取飞书访问令牌")
    except Exception as e:
        print(f"❌ 获取 Token 失败：{e}")
        return
    
    # 获取群 ID
    print("\n📋 当前配置:")
    print(f"   App ID: {app_id}")
    print()
    
    chat_id = get_group_chat_id(token)
    
    if chat_id:
        # 保存到配置文件
        config['lark_config']['chat_id'] = chat_id
        config['chat_id_last_updated'] = datetime.now().isoformat()
        
        try:
            with open('lark_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print()
            print(f"✅ 群 ID 已保存：{chat_id}")
            print("   配置文件已更新：lark_config.json")
            
            # 验证群 ID
            try:
                # 尝试获取群信息
                url = f"https://open.feishu.cn/open-apis/chat/v2/get?chat_id={chat_id}"
                headers = {
                    "Authorization": f"Bearer {token}"
                }
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        chat_info = data.get("data", {}).get("chat", {})
                        print(f"\n✅ 群 ID 验证成功!")
                        print(f"   群名：{chat_info.get('name', '未知')}")
                        print(f"   群类型：{chat_info.get('chat_type', '未知')}")
                        print(f"   成员数：{chat_info.get('member_count', '未知')}")
                    else:
                        print(f"\n⚠️  群 ID 可能无效：{data.get('msg')}")
                else:
                    print(f"\n⚠️  无法验证群 ID: HTTP {response.status_code}")
            except Exception as e:
                print(f"\n⚠️  群 ID 验证跳过：{e}")
            
        except Exception as e:
            print(f"❌ 保存配置失败：{e}")
    else:
        print("\n⚠️  未获取到群 ID")
        print("   请先获取飞书群 ID 后重试")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
