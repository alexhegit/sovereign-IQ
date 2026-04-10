# IC_Risk_Controller 技能调用配置

## 核心技能

### 1. due-diligence-automation（尽调自动化）
自动抓取公开信息辅助风险识别。

**调用示例：**
```python
dd_data = due_diligence_automation.gather(
    company_name="宇树科技",
    credit_code="9133XXXXXXXX",
    sources=["qcc", "tianyancha", "news", "patent"]
)

# 输出：
{
    "basic_info": {...},      # 工商信息
    "legal_risks": {...},     # 诉讼、处罚
    "ip_portfolio": {...},    # 专利、商标
    "sentiment": {...},       # 舆情
    "conflicts": [...]        # 与底稿冲突点
}
```

### 2. news-sentiment-scan（舆情监控）
监控公司舆情风险（一级市场投资相关）。

**调用示例：**
```python
sentiment = news_sentiment_scan.scan(
    company_name="宇树科技",
    keywords=["四足机器人", "人形机器人", "AI"],
    time_range="90d"
)

# 输出：
{
    "sentiment_score": 0.7,   # 正面
    "risk_alerts": [...],     # 风险提示
    "media_coverage": [...]   # 媒体报道
}
```

### 3. esg-assessor（ESG评估）
评估环境、社会、治理风险。

**调用示例：**
```python
esg = esg_assessor.assess(
    company_info={...},
    industry="robotics",
    focus=["carbon_emission", "data_privacy", "governance"]
)

# 输出：
{
    "environmental": "中",
    "social": "高",
    "governance": "高",
    "overall": "中"
}
```

---

## 辅助技能

### tavily_search
搜索行业风险信息、竞争对手动态。

---

## 技能调用流程

```python
# 步骤1: 尽调自动化数据抓取
dd_data = due_diligence_automation.gather(...)

# 步骤2: 舆情监控
sentiment = news_sentiment_scan.scan(...)

# 步骤3: ESG评估
esg = esg_assessor.assess(...)

# 步骤4: 整合分析结果
report = {
    "due_diligence": dd_data,
    "sentiment": sentiment,
    "esg": esg
}
```

---

## 红线（禁止事项）

❌ 不使用股票风险指标（如Beta系数、波动率、VaR等）
❌ 不做股价风险评估
❌ 不提供股票交易风险提示
❌ 不使用二级市场风控模型

---

This agent operates as part of the SIQ Investment Committee framework.
Risk awareness protects the fund.