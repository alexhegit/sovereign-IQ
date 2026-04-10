# TOOLS.md - SIQ 投委会财务专家

## 工具清单

### wilcox_valuation_engine()
计算企业估值带，输出 Wilcox PB-ROE 校准结果。

### dcf_stress_test()
执行多维度现金流压力测试，动态修正折现率 r 与长期增长率 g，输出敏感性分析矩阵。

### fire_metrics_analyzer()
计算 FIRE 指标（NRR、Gross Margin、LTV/CAC、Burn Multiple），评估 SaaS 健康度。

### stage_appropriate_valuation()
根据项目阶段自动选择估值方法：Pre-Seed 用 Berkus/Scorecard，Series A 用 VC Method，Series B+ 用 DCF+Multiples。
