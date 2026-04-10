# IC_Finance_Auditor 技能调用配置

## 核心技能

### 1. primary-market-valuation（一级市场估值）
针对Pre-Seed到Pre-IPO各阶段的估值计算。

**调用示例：**
```python
valuation = primary_market_valuation.calculate(
    stage="Series B",           # 阶段
    arr=50000000,              # ARR
    growth_rate=1.5,           # 增长率
    industry="SaaS",           # 行业
    region="China",            # 地区
    gov_lp_involved=True       # 是否有国资LP
)

# 输出：
{
    "valuation_range": "4-6亿RMB",
    "method": "Revenue Multiple",
    "market_comps": ["公司A: 8x", "公司B: 10x"],
    "gov_lp_adjustment": "国资条款-10%估值折扣",
    "confidence": "medium"
}
```

### 2. financial-health-checker（财务健康检查）
分析收入质量、现金流、单位经济。

**调用示例：**
```python
health = financial_health_checker.analyze(
    financial_statements="path/to/financials.pdf",
    metrics=["recurring_revenue", "gross_margin", "ltv_cac", "burn_rate"]
)

# 输出：
{
    "revenue_quality": "高",
    "cash_flow": "健康",
    "unit_economics": "可持续",
    "runway": "18个月"
}
```

### 3. gov-lp-compliance（国资LP合规检查）
检查国资条款、产业落地要求、退出机制。

**调用示例：**
```python
gov_check = gov_lp_compliance.check(
    gov_lp_type="政府引导基金",
    local_gov_requirement="税收+就业",
    exit_terms={"repurchase_rate": "8%", "timeline": "7年"}
)

# 输出：
{
    "match_score": "高",
    "landed_cost": "税收500万/年，就业100人",
    "exit_risk": "低",
    "recommendation": "可争取国资支持"
}
```

---

## 辅助技能

### tavily_search
搜索可比公司估值、行业财务数据。

---

## 技能调用流程

```python
# 步骤1: 获取估值区间
valuation = primary_market_valuation.calculate(...)

# 步骤2: 检查财务健康度
health = financial_health_checker.analyze(...)

# 步骤3: 国资LP合规检查（如适用）
gov_check = gov_lp_compliance.check(...)

# 步骤4: 整合分析结果
report = {
    "valuation": valuation,
    "financial_health": health,
    "gov_lp": gov_check
}
```

---

## 红线（禁止事项）

❌ 不使用股票技术分析工具（K线/RSI/MACD等）
❌ 不提供股票交易建议
❌ 不做短期股价预测
❌ 不使用二级市场估值指标（P/E、Beta等）

---

This agent operates as part of the SIQ Investment Committee framework.
Financial rigor grounds investment decisions.