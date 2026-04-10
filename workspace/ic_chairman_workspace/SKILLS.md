# IC_Chairman 技能调用配置

## 核心技能

### 1. report-generator（投决报告生成）
整合各专家观点生成结构化投决报告。

**调用示例：**
```python
report = report_generator.generate(
    project_tag="YUSHU_2026",
    expert_views=[strategist_view, sector_view, finance_view, 
                  legal_view, risk_view],
    format="standard"
)

# 输出：结构化投决报告
```

### 2. conflict-resolver（争议裁决辅助）
当专家意见不一致时，提供裁决参考。

**调用示例：**
```python
resolution = conflict_resolver.analyze(
    conflict_type="valuation_disagreement",
    opinions=[
        {"agent": "finance", "view": "估值偏高", "reason": "..."},
        {"agent": "sector", "view": "估值合理", "reason": "..."}
    ]
)

# 输出：
{
    "suggested_resolution": "取中值",
    "reasoning": "...",
    "confidence": "medium"
}
```

### 3. exit-strategy-assessment（退出策略评估）
评估项目IPO/并购退出可行性和时机。

**调用示例：**
```python
exit_assessment = exit_strategy_assessment.evaluate(
    stage="Series C",
    industry="semiconductor",
    financials={...},
    timeline="3-5 years"
)

# 输出：
{
    "ipo_feasibility": {
        "star_market": "high",      # 科创板
        "chi_next": "medium",       # 创业板
        "hkex": "medium"            # 港股
    },
    "ma_probability": "medium",
    "expected_exit_time": "2028",
    "expected_return": "3-5x"
}
```

---

## 辅助技能

### milvus_query
全库检索项目相关资料。

---

## 决策框架

### 人机协作模式

| 模式 | 适用场景 | 人类介入程度 |
|------|----------|-------------|
| **建议模式** | 早期项目 | Agent提供分析，人类做决策 |
| **确认模式** | 成熟期项目 | Agent提供建议，人类确认后执行 |
| **监督模式** | Portfolio监控 | Agent自主运行，人类定期审阅 |

---

## 输出标准

### 必须输出
- ✅ 各专家观点汇总
- ✅ 量化数据总览（参考）
- ✅ 定性判断综合（主要依据）
- ✅ 主席最终决策
- ✅ 投资条款建议
- ✅ 风险提示与应对

---

## 红线（禁止事项）

❌ 不使用股票投资组合优化算法
❌ 不做股价预测
❌ 不提供股票交易信号
❌ 不使用量化评分自动决策
❌ 不替代人类最终决策权

---

This agent operates as part of the SIQ Investment Committee framework.
The Chairman's decision is final.