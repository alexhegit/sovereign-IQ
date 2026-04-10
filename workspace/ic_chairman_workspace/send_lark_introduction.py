#!/usr/bin/env python3
"""
SIQ 投委会主席 - 飞书群自我介绍
使用当前对话的群 ID 发送自我介绍
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

def send_introduction(chat_id, token):
    """发送自我介绍"""
    introduction_message = """🏛️ SIQ 投委会主席 (ic_chairman) 自我介绍

各位好！

我是 SIQ 投资委员会主席 **ic_chairman**，负责投委会的最终决策、冲突裁决和战略对齐。

🎯 我的职责
- 最终决策：综合各专家意见，做出投/不投的最终决定
- 冲突裁决：处理投委会内部的分歧，确保决策质量
- 战略对齐：确保每项投资符合 SIQ 长期战略目标

📊 核心能力
- 六维评估矩阵（市场、团队、产品、财务、风险、战略）
- Go/No-Go 决策树（红黄线标准）
- 投后管理视角

🤝 协作方式
- 财务专家：挑战核心假设，要求提供替代方案
- 法律专家：绝不为了效率牺牲合规性
- 风控专家：尊重风险红线，深度理解风险逻辑
- 战略师：确保投资与基金战略高度一致
- 行业专家：深度钻研行业本质，持续学习
- IC 秘书：提供清晰的流程和决策支持

📜 决策原则
1. 数据提供信息，智慧做出决定
2. 决策需要勇气：有时必须果断说"不"
3. 长期主义致胜：追求基业长青
4. 冲突具有价值：分歧是最佳路径的敲门砖

📞 使用方式
- 项目评估：提交尽调报告，我会综合分析
- 决策支持：需要快速建议或深入分析
- 冲突裁决：需要投委会内部分歧裁决
- 战略咨询：需要投资建议或风险评估

🏛️ 准备好为 SIQ 的长期价值贡献力量。

请各位多指教！有任何项目评估或决策需求，随时提出。

"""
    
    url = "https://open.feishu.cn/open-apis/message/v4/send"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "chat_id": chat_id,
        "msg_type": "text",
        "content": {
            "text": introduction_message
        }
    }
    
    print(f"\n📤 发送到群聊：{chat_id}")
    print(f"📝 消息内容预览 (前 100 字符):")
    print(f"   {introduction_message[:100]}...")
    print()
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 0:
            print("✅ 消息发送成功!")
            print(f"   发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        else:
            print(f"❌ 飞书 API 错误：{data.get('msg')}")
            return False
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False

def main():
    """主函数"""
    print("=" * 70)
    print("  SIQ 投委会主席 - 飞书群自我介绍")
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
    
    # 获取群聊 ID
    chat_id = config.get('lark_config', {}).get('chat_id')
    
    if not chat_id:
        print("\n⚠️  未找到配置的群聊 ID (chat_id)")
        print("   请提供您想发送自我介绍的飞书群 ID")
        print("   (在飞书群聊详情中获取，以 chat_ 开头)")
        print()
        print("当前飞书配置:")
        print(f"   App ID: {app_id}")
        return
    
    # 发送自我介绍
    print()
    print(f"📋 群聊 ID: {chat_id}")
    print("=" * 70)
    
    success = send_introduction(chat_id, token)
    
    if success:
        print("\n" + "=" * 70)
        print("🏛️ SIQ 投委会主席已开始在飞书群活跃!")
        print("=" * 70)
    else:
        print("\n❌ 自我介绍发送失败")
        print("   请检查群 ID 是否正确，或者联系群主确认权限")
    
    print()

if __name__ == "__main__":
    main()
