#!/bin/bash
# 为 AI 投委会秘书配置飞书文档知识库

source ~/.openclaw/.env.feishu-ic 2>/dev/null || true

# 如果没有环境变量，从 OpenClaw 配置读取
APP_ID="${FEISHU_APP_ID:-cli_a9467d11b438dbc6}"
APP_SECRET="${FEISHU_APP_SECRET:-jzioMc7zi78z9TXwZeszEeKUvBMBmAmX}"

echo "🤖 AI 投委会秘书飞书知识库配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "App ID: $APP_ID"
echo "状态：已配置"
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

# 检查文档权限
PERMISSIONS=$(curl -s -X POST "https://open.feishu.cn/open-apis/drive/v1/batch_get_permission_infos" \
    -H "Authorization: Bearer $TENANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"driver_id": "drivecloud"}' 2>&1)

echo "📋 飞书文档权限检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if echo "$PERMISSIONS" | grep -q '"code":0'; then
    echo "✅ 飞书文档 API 权限正常"
else
    echo "⚠️  文档 API 可能未授权"
    echo "响应：$PERMISSIONS"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 投委会秘书可用飞书功能："
echo ""
echo "1️⃣  飞书知识库"
echo "   • 创建投决会决策记录文档"
echo "   • 存储项目尽调报告"
echo "   • 管理投资案例库"
echo ""
echo "2️⃣  飞书群组通知"
echo "   • IC 会议提醒"
echo "   • 决策结果通知"
echo "   • 进度更新"
echo ""
echo "3️⃣  飞书文档协作"
echo "   • 协作者权限管理"
echo "   • 版本控制"
echo "   • 批注与评论"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 下一步："
echo "   • 在飞书群组添加机器人后，提供 Chat ID"
echo "   • 发送测试消息验证连接"
echo "   • 开始使用飞书存储投委会决策记录"
echo ""
