# IC_Legal_Scanner 技能调用配置

## 辅助技能：news-sentiment-scan

### 调用场景
监控与公司法律合规相关的舆情风险。

### 技能调用示例

```python
# 扫描法律相关舆情
legal_sentiment = news_sentiment_scan.scan(
    keywords=["公司名称", "诉讼", "仲裁", "处罚", "监管"],
    sources=["新闻", "公告", "社交媒体"],
    time_range="180d",  # 关注半年内的法律舆情
    risk_focus=True     # 重点关注负面信息
)

# 输出：
# - 法律相关情绪评分
# - 负面舆情预警
# - 风险关键词
```

## 与其他角色的配合

| 角色 | 输入 | 输出 |
|------|------|------|
| Risk Controller | 法律舆情风险 | 获得舆情层面的法律风险补充 |
| Finance Auditor | 重大合同条款 | 交叉验证合同财务风险 |
| Chairman | 法律风险评估 | 辅助最终决策 |

## 法律尽调流程

```
任务：法律合规尽调

Step 1: 审查法律文件（尽调底稿）
- 公司主体/股权结构
- 重大合同
- 知识产权
- 诉讼处罚

Step 2: 调用 news-sentiment-scan（辅助）
扫描公开渠道的法律舆情

Step 3: 综合评估
整合文件审查 + 舆情监控
输出：法律风险评级（🟢🟡🔴）
```

## 注意事项

⚠️ 本角色专注于微观法律合规：
- ✅ 合同条款审查
- ✅ IP权属验证
- ✅ 诉讼仲裁记录
- ✅ 监管处罚
- ✅ 数据合规PIPL
- ❌ 不分析宏观政策（Strategist负责）
- ❌ 不评估市场风险（Risk Controller负责）
- ❌ 不计算财务指标（Finance Auditor负责）
