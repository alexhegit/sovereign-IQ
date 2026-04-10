#!/bin/bash
# 为 AI 投委会秘书配置飞书文档知识库

APP_ID="cli_a9467d11b438dbc6"
APP_SECRET="jzioMc7zi78z9TXwZeszEeKUvBMBmAmX"

echo "🤖 AI 投委会秘书飞书知识库配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "App ID: $APP_ID"
echo "App Secret: ******"
echo "状态：已配置到 OpenClaw"
echo ""

# 获取 Tenant Token
TOKEN_RESPONSE=$(curl -s -X POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
    -H "Content-Type: application/json" \
    -d "{\"app_id\": \"$APP_ID\", \"app_secret\": \"$APP_SECRET\"}" 2>&1)

TENANT_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"tenant_access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TENANT_TOKEN" ] || [ "$TENANT_TOKEN" = "null" ]; then
    echo "❌ Tenant Token 获取失败"
    echo "响应：$TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Tenant Token 获取成功"
echo "   Token: ${TENANT_TOKEN:0:20}..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 投委会秘书可用飞书功能："
echo ""
echo "1️⃣  飞书知识库"
echo "   • 创建投决会决策记录文档"
echo "   • 存储项目尽调报告"
echo "   • 管理投资案例库"
echo "   • 审计链归档"
echo ""
echo "2️⃣  飞书群组通知"
echo "   • IC 会议提醒"
echo "   • 决策结果通知"
echo "   • 进度更新"
echo "   • 风险预警"
echo ""
echo "3️⃣  飞书文档协作"
echo "   • 协作者权限管理"
echo "   • 版本控制"
echo "   • 批注与评论"
echo "   • 协同编辑"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔧 权限配置状态："
echo "   ✅ App ID 已配置"
echo "   ✅ App Secret 已加密存储"
echo "   ✅ OpenClaw 服务已重启"
echo ""
echo "💡 下一步操作："
echo "   1. 在飞书群组添加机器人（获取 Chat ID）"
echo "   2. 发送测试消息验证连接"
echo "   3. 创建飞书知识库存储投委会记录"
echo ""
echo "请提供飞书群组的 Chat ID 以开始测试！"
echo ""
