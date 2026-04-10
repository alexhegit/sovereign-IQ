# TOOLS.md - SIQ 投委会秘书/协调者

## 核心工具

### 1. orchestrate_task_graph()
启动 6 位专家并行尽调，T+7 交付标准，R1严格串行发言。

**调用方式（固定Agent，禁止创建Subagent）：**
```python
# R1阶段 - 严格串行发言顺序
# 1. 战略专家（权重15%）
sessions_send(
    sessionKey="ic_strategist", 
    message="【R1任务】分析宇树科技宏观战略...",
    agentId="ic-strategist"
)

# 2. 行业专家（权重15%）
sessions_send(
    sessionKey="ic_sector_expert",
    message="【R1任务】分析机器人赛道竞争格局...",
    agentId="ic-sector-expert"
)

# 3. 财务专家（权重15%）
sessions_send(
    sessionKey="ic_finance_auditor",
    message="【R1任务】进行估值分析...",
    agentId="ic-finance-auditor"
)

# 4. 法务专家（权重10%）
sessions_send(
    sessionKey="ic_legal_scanner",
    message="【R1任务】进行法律合规审查...",
    agentId="ic-legal-scanner"
)

# 5. 风控专家（权重15%）
sessions_send(
    sessionKey="ic_risk_controller",
    message="【R1任务】进行风险评估...",
    agentId="ic-risk-controller"
)

# 6. 投委会主席（权重30%，R1可选，R1.5/R3必选）
sessions_send(
    sessionKey="ic_chairman",
    message="【R1.5中期裁决】请裁决以下争议点...",
    agentId="ic-chairman"
)
```

**固定Agent列表（权重V2已固化）：**
| Agent ID | 角色 | 权重 | R1顺序 | R2任务 | R3立场 |
|----------|------|------|--------|--------|--------|
| `ic_strategist` | 战略专家 | 15% | 第1位 | 完善战略观点 | 🔵蓝方 |
| `ic_sector_expert` | 行业专家 | 15% | 第2位 | 完善行业观点 | 🔵蓝方 |
| `ic_finance_auditor` | 财务专家 | 15% | 第3位 | 完善估值观点 | 🔴红方 |
| `ic_legal_scanner` | 法务专家 | 10% | 第4位 | 完善法务观点 | 🔵蓝方 |
| `ic_risk_controller` | 风控委员 | 15% | 第5位 | 完善风险观点 | 🔴红方 |
| `ic_chairman` | 投委会主席 | 30% | 第6位(可选) | 综合裁决 | 裁决者 |

---

### 2. calculate_weighted_score()
**核心功能：计算加权投决评分**

**输入：**
```json
{
  "chairman": 75,
  "strategy": 90,
  "sector": 80,
  "finance": 55,
  "risk": 65,
  "legal": 85
}
```

**权重配置 V2（已固化）：**
```python
WEIGHTS = {
    "chairman": 0.30,
    "strategy": 0.15,
    "sector": 0.15,
    "finance": 0.15,
    "risk": 0.15,
    "legal": 0.10
}
```

**计算过程：**
```python
def calculate_weighted_score(scores):
    """
    计算加权投决评分
    
    参数：
        scores: dict, 各专家评分（0-100）
    
    返回：
        dict, 包含总分、各分项加权得分、决策结果
    """
    WEIGHTS = {
        "chairman": 0.30,
        "strategy": 0.15,
        "sector": 0.15,
        "finance": 0.15,
        "risk": 0.15,
        "legal": 0.10
    }
    
    THRESHOLD = 70  # 通过阈值（已固化）
    
    weighted_scores = {}
    total_score = 0
    
    for role, score in scores.items():
        weighted = score * WEIGHTS[role]
        weighted_scores[role] = {
            "raw_score": score,
            "weight": WEIGHTS[role],
            "weighted_score": round(weighted, 2)
        }
        total_score += weighted
    
    # 决策判定
    if total_score >= THRESHOLD:
        decision = "pass"  # ✅ 通过
    else:
        decision = "reject"  # ❌ 不通过
    
    # 复议机制检查
    review_eligible = 68 <= total_score < 70
    
    return {
        "total_score": round(total_score, 2),
        "threshold": THRESHOLD,
        "decision": decision,
        "review_eligible": review_eligible,
        "breakdown": weighted_scores
    }

# 使用示例（宇树科技）
scores = {
    "chairman": 75,
    "strategy": 90,
    "sector": 80,
    "finance": 55,
    "risk": 65,
    "legal": 85
}

result = calculate_weighted_score(scores)
print(f"总分：{result['total_score']}")  # 74.50
print(f"决策：{result['decision']}")     # pass
print(f"可复议：{result['review_eligible']}")  # False
```

---

### 3. identify_disputes()
**核心功能：R1.5阶段自动识别争议点**

**争议识别规则：**
```python
def identify_disputes(r1_reports):
    """
    识别R1阶段争议点
    
    触发条件（满足任一）：
    1. 估值差异 > 20%
    2. 风险评级差异 ≥ 1个等级（🟢🟡🔴）
    3. 投资建议完全相反（支持 vs 反对）
    
    返回：争议点列表，供Chairman中期裁决
    """
    disputes = []
    
    # 规则1：估值差异 > 20%
    valuations = extract_valuations(r1_reports)
    if max(valuations) / min(valuations) > 1.2:
        disputes.append({
            "type": "valuation_gap",
            "severity": "high",
            "description": f"估值差异{max(valuations)/min(valuations):.0%}，需裁决合理区间"
        })
    
    # 规则2：风险评级差异
    risk_ratings = extract_risk_ratings(r1_reports)
    if has_rating_conflict(risk_ratings):
        disputes.append({
            "type": "risk_rating_conflict",
            "severity": "medium",
            "description": "风险评级存在分歧，需统一认知"
        })
    
    # 规则3：投资建议相反
    recommendations = extract_recommendations(r1_reports)
    if has_opposite_recommendations(recommendations):
        disputes.append({
            "type": "opposite_recommendation",
            "severity": "high",
            "description": "投资建议完全相反，需明确方向"
        })
    
    return disputes
```

---

### 4. cross_validate_data()
数据一致性检查，三方交叉验证，标记争议点。

**交叉验证维度：**
- 估值数据：财务专家 vs 行业对标 vs 公开信息
- 风险数据：风控专家 vs 法务专家 vs 公开舆情
- 战略数据：战略专家 vs 行业专家 vs 政策文件

**标记规则：**
- 差异 < 10%：✅ 一致
- 差异 10-20%：🟡 轻微分歧
- 差异 > 20%：🔴 重大争议（提交R1.5裁决）

---

### 5. generate_audit_log()
生成完整审计链，7 年保存，可追溯所有决策点。

**审计链格式：**
```json
{
  "project_id": "SIQ-UNITREE-2026-001",
  "project_name": "宇树科技",
  "timestamp_start": "2026-04-06T04:56:00Z",
  "timestamp_end": "2026-04-06T06:43:00Z",
  "total_duration_minutes": 107,
  
  "weighted_decision": {
    "version": "V2",
    "weights": {
      "chairman": 0.30,
      "strategy": 0.15,
      "sector": 0.15,
      "finance": 0.15,
      "risk": 0.15,
      "legal": 0.10
    },
    "scores": {
      "chairman": 75,
      "strategy": 90,
      "sector": 80,
      "finance": 55,
      "risk": 65,
      "legal": 85
    },
    "weighted_scores": {
      "chairman": 22.50,
      "strategy": 13.50,
      "sector": 12.00,
      "finance": 8.25,
      "risk": 9.75,
      "legal": 8.50
    },
    "total_score": 74.50,
    "threshold": 70,
    "decision": "pass",
    "review_eligible": false
  },
  
  "timeline": [
    {
      "timestamp": "2026-04-06T04:56:00Z",
      "agent": "IC_Master_Coordinator",
      "action": "Project_Initiated",
      "details": "宇树科技项目启动，6位专家初始化"
    },
    {
      "timestamp": "2026-04-06T05:05:00Z",
      "agent": "ic_strategist",
      "action": "R1_Report_Submitted",
      "weight": 0.15,
      "score": 90,
      "confidence": "High"
    },
    {
      "timestamp": "2026-04-06T05:30:00Z",
      "agent": "IC_Chairman",
      "action": "R1.5_MidTerm_Ruling",
      "disputes_resolved": 2
    },
    {
      "timestamp": "2026-04-06T06:43:00Z",
      "agent": "IC_Chairman",
      "action": "Final_Decision",
      "weighted_score": 74.50,
      "decision": "pass"
    }
  ],
  
  "human_decision_points": [
    {
      "point": "底稿入库",
      "timestamp": "2026-04-06T04:58:00Z",
      "decision": "approved"
    },
    {
      "point": "中期裁决确认",
      "timestamp": "2026-04-06T05:35:00Z",
      "decision": "approved"
    },
    {
      "point": "归档审核",
      "timestamp": "2026-04-06T07:00:00Z",
      "decision": "pending"
    }
  ],
  
  "export_date": "2026-04-06T06:43:00Z",
  "retention_years": 7
}
```

---

### 6. ic_report_formatter()
IC 决策报告格式化，统一模板输出。

**报告模板：**
```markdown
# SIQ 投委会投资决策报告

## 项目信息
- 项目名称：{project_name}
- 项目编号：{project_id}
- 报告日期：{date}
- 决策结果：{decision}

## 加权决策结果
| 角色 | 权重 | 评分 | 加权得分 |
|------|------|------|----------|
| Chairman | 30% | {score} | {weighted} |
| Strategy | 15% | {score} | {weighted} |
| Sector | 15% | {score} | {weighted} |
| Finance | 15% | {score} | {weighted} |
| Risk | 15% | {score} | {weighted} |
| Legal | 10% | {score} | {weighted} |
| **总计** | **100%** | - | **{total_score}** |

**阈值判定：** {total_score}分 {comparison} 70分 → {decision}

## 六维评估摘要
[各维度评估摘要]

## 争议点与裁决
[R1.5中期裁决记录]
[R3红蓝对抗要点]

## 投资建议
- 估值区间：{valuation_range}
- 配置比例：{allocation}
- 关键条款：{key_terms}
- 风险提示：{risk_warnings}

## 审计链
[审计日志附件]
```

---

## 复议机制工具

### review_mechanism()
**触发条件：** 68分 ≤ 评分 < 70分

**流程：**
```python
def review_mechanism(project_id, new_evidence):
    """
    复议机制
    
    限制：
    - 仅限1次复议
    - 需提交补充材料
    - 可指定1-2位专家重新评分
    """
    # 1. 验证复议资格
    if not is_review_eligible(project_id):
        return {"error": "不符合复议条件"}
    
    # 2. 指定专家重新评分
    reviewers = select_reviewers(project_id, count=2)
    new_scores = request_rescore(reviewers, new_evidence)
    
    # 3. 重新计算总分
    updated_scores = update_scores(original_scores, new_scores)
    final_result = calculate_weighted_score(updated_scores)
    
    # 4. 标记复议已使用
    mark_review_used(project_id)
    
    return final_result
```

---

## 配置常量（已固化）

```python
# 权重配置 V2（不可调整）
WEIGHTS_V2 = {
    "chairman": 0.30,
    "strategy": 0.15,
    "sector": 0.15,
    "finance": 0.15,
    "risk": 0.15,
    "legal": 0.10
}

# 决策阈值 V2（不可调整）
THRESHOLD_PASS = 70
THRESHOLD_REVIEW_MIN = 68
THRESHOLD_REVIEW_MAX = 69

# 时间限制
R1_TIMEOUT = 300  # 5分钟/专家
R2_TIMEOUT = 1200  # 20分钟
R3_TIMEOUT = 1200  # 20分钟
TOTAL_SLA = 4200  # 70分钟

# 争议识别阈值
VALUATION_GAP_THRESHOLD = 0.20  # 20%
```

---

*工具版本：V2 | 权重已固化 | 阈值已固化*
