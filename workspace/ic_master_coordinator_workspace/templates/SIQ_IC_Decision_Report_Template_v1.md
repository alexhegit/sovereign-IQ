# SIQ投委会 · 一级市场投研决策报告模板

> **模板版本**: v1.0  
> **生效日期**: 2026-04-06  
> **归属**: ic_master_coordinator（秘书负责生成）  
> **审核**: ic_chairman（主席负责审核）

---

## 一、项目信息

| 项目 | 详情 |
|------|------|
| **项目名称** | {project_name} |
| **项目编号** | {project_id} |
| **赛道** | {sector} |
| **轮次** | {round} |
| **建议估值** | {valuation_range} |
| **建议配置** | {allocation} |
| **报告日期** | {date} |
| **投决总分** | **{total_score}分 / 100分** |
| **决策结果** | {decision} |

---

## 二、六维专家评估详述

### 1️⃣ ic_strategist（战略专家）权重15%
**评分：{strategy_score}分（{strategy_rating}）**

#### 核心观点

| 维度 | 判断 | 依据 |
|------|------|------|
| **赛道β** | {strategy_sector} | {strategy_sector_reason} |
| **政策趋势** | {strategy_policy} | {strategy_policy_reason} |
| **资金流向** | {strategy_capital} | {strategy_capital_reason} |
| **地缘风险** | {strategy_geopolitics} | {strategy_geopolitics_reason} |

#### 关键结论
> {strategy_conclusion}

---

### 2️⃣ ic_sector_expert（行业专家）权重15%
**评分：{sector_score}分（{sector_rating}）**

#### 核心观点

| 维度 | 判断 | 依据 |
|------|------|------|
| **技术竞争力** | {sector_tech} | {sector_tech_reason} |
| **竞争格局** | {sector_competition} | {sector_competition_reason} |
| **商业模式** | {sector_business_model} | {sector_business_model_reason} |
| **团队能力** | {sector_team} | {sector_team_reason} |

#### 关键结论
> {sector_conclusion}

---

### 3️⃣ ic_finance_auditor（财务审计委员）权重15%
**评分：{finance_score}分（{finance_rating}）**

#### 核心观点

| 维度 | 判断 | 依据 |
|------|------|------|
| **估值合理性** | {finance_valuation} | {finance_valuation_reason} |
| **财务健康度** | {finance_health} | {finance_health_reason} |
| **收入质量** | {finance_revenue} | {finance_revenue_reason} |
| **盈利能力** | {finance_profit} | {finance_profit_reason} |

#### 估值模型

| 情景 | 估值区间 | 概率 | 核心假设 |
|------|----------|------|----------|
| **乐观** | {finance_bull_valuation} | {finance_bull_prob} | {finance_bull_assumption} |
| **基准** | {finance_base_valuation} | {finance_base_prob} | {finance_base_assumption} |
| **悲观** | {finance_bear_valuation} | {finance_bear_prob} | {finance_bear_assumption} |

#### 关键结论
> {finance_conclusion}

---

### 4️⃣ ic_legal_scanner（法务合规委员）权重10%
**评分：{legal_score}分（{legal_rating}）**

#### 核心观点

| 维度 | 判断 | 依据 |
|------|------|------|
| **知识产权** | {legal_ip} | {legal_ip_reason} |
| **股权结构** | {legal_equity} | {legal_equity_reason} |
| **诉讼风险** | {legal_litigation} | {legal_litigation_reason} |
| **出口管制** | {legal_export} | {legal_export_reason} |

#### TS保护条款建议

| 条款 | 内容 | 目的 |
|------|------|------|
| {legal_ts_clause_1} | {legal_ts_content_1} | {legal_ts_purpose_1} |
| {legal_ts_clause_2} | {legal_ts_content_2} | {legal_ts_purpose_2} |

#### 关键结论
> {legal_conclusion}

---

### 5️⃣ ic_risk_controller（风险管理委员）权重15%
**评分：{risk_score}分（{risk_rating}）**

#### 核心观点

| 风险维度 | 等级 | 关键结论 |
|----------|------|----------|
| **市场风险** | {risk_market_level} | {risk_market_conclusion} |
| **供应链风险** | {risk_supply_chain_level} | {risk_supply_chain_conclusion} |
| **舆情风险** | {risk_public_level} | {risk_public_conclusion} |
| **行业周期** | {risk_cycle_level} | {risk_cycle_conclusion} |

#### 关键风险量化

| 指标 | 数值 |
|------|------|
| **触发概率** | {risk_trigger_prob} |
| **预期损失** | {risk_expected_loss} |

#### 关键结论
> {risk_conclusion}

---

### 6️⃣ ic_chairman（投委会主席）权重30%
**评分：{chairman_score}分（{chairman_rating}）**

#### 综合判断

| 维度 | 评估 |
|------|------|
| **赛道方向** | {chairman_sector} |
| **公司地位** | {chairman_company} |
| **投资时机** | {chairman_timing} |
| **风险可控** | {chairman_risk} |
| **团队能力** | {chairman_team} |

#### 争议点裁决

| 争议 | 蓝方观点 | 红方观点 | **Chairman裁决** |
|------|---------|---------|------------------|
| {dispute_1_topic} | {dispute_1_blue} | {dispute_1_red} | **{dispute_1_ruling}** |
| {dispute_2_topic} | {dispute_2_blue} | {dispute_2_red} | **{dispute_2_ruling}** |

#### 关键结论
> {chairman_conclusion}

---

## 三、加权决策计算

### 权重分布（V2已固化）

| 角色 | 权重 | 评分 | 加权得分 | 计算过程 |
|------|------|------|----------|----------|
| **Chairman** | 30% | {chairman_score} | **{chairman_weighted}** | {chairman_score} × 0.30 = {chairman_weighted} |
| **战略** | 15% | {strategy_score} | **{strategy_weighted}** | {strategy_score} × 0.15 = {strategy_weighted} |
| **行业** | 15% | {sector_score} | **{sector_weighted}** | {sector_score} × 0.15 = {sector_weighted} |
| **财务** | 15% | {finance_score} | **{finance_weighted}** | {finance_score} × 0.15 = {finance_weighted} |
| **风控** | 15% | {risk_score} | **{risk_weighted}** | {risk_score} × 0.15 = {risk_weighted} |
| **法务** | 10% | {legal_score} | **{legal_weighted}** | {legal_score} × 0.10 = {legal_weighted} |

### 最终判定

```
投决总分 = {chairman_weighted} + {strategy_weighted} + {sector_weighted} + {finance_weighted} + {risk_weighted} + {legal_weighted}
        = {total_score}分

阈值判定：{total_score}分 {comparison} 70分
决策结果：{decision}
```

---

## 四、投资建议

### ✅ 核心投资逻辑

| 因素 | 支持点 |
|------|--------|
| **赛道β** | {investment_logic_1} |
| **公司α** | {investment_logic_2} |
| **资本质量** | {investment_logic_3} |
| **风险对冲** | {investment_logic_4} |

### ⚠️ 关键风险提示

| 风险 | 等级 | 监控指标 |
|------|------|----------|
| {risk_1_name} | {risk_1_level} | {risk_1_monitor} |
| {risk_2_name} | {risk_2_level} | {risk_2_monitor} |

### 📋 投资条件清单（必须满足）

| # | 条件 | 说明 |
|---|------|------|
| 1 | {condition_1} | {condition_1_detail} |
| 2 | {condition_2} | {condition_2_detail} |
| 3 | {condition_3} | {condition_3_detail} |

---

## 五、后续行动

| 时间 | 行动 | 负责方 |
|------|------|--------|
| T+1 | {action_1} | {action_1_owner} |
| T+7 | {action_2} | {action_2_owner} |
| T+14 | {action_3} | {action_3_owner} |

---

**报告生成**：ic_master_coordinator（SIQ投委会秘书）  
**审核状态**：待ic_chairman最终确认  
**归档路径**：`ic_collaboration_shared_ws/{project_id}-Final-Report.md`
