# TaskGraph 协议定义
## Sovereign-IQ V2.0 任务调度协议

---

## 1. 协议概述

TaskGraph 协议是 Sovereign-IQ V2.0 的核心调度机制，基于有向无环图（DAG）实现多 Agent 并发任务编排，支持自愈式任务扩展与条件触发逻辑。

---

## 2. 节点类型

| 节点类型 | 说明 | 示例 |
|----------|------|------|
| `task` | 原子任务，由单一 Agent 执行 | `财务估值`、`法务扫描` |
| `gateway` | 条件网关，控制任务分支 | `AML通过?` |
| `subgraph` | 子流程，包含嵌套任务组 | `自愈循环`、`对抗辩论` |
| `merge` | 聚合节点，汇总多路输入 | `报告合成` |

---

## 3. 全局任务图定义

```yaml
 sovereign_iq_v2:
   project_id: "<自动生成>"
   
   stages:
     stage_1_admission:
       type: subgraph
       nodes:
         - receive_project
         - load_knowledge_isolation
         - aml_kyc_check
       edges:
         - receive_project → aml_kyc_check
         - load_knowledge_isolation → aml_kyc_check
       gateway:
         condition: "aml_passed == true"
         true_branch: "stage_2_parallel_investigation"
         false_branch: "stage_reject"
   
     stage_2_parallel_investigation:
       type: subgraph
       concurrency: 4  # 4个Agent并发
       parallel_nodes:
         - finance_valuation: "IC_Auditor"
         - sector_analysis: "IC_Sector_Expert"
         - policy_alignment: "IC_Strategist"
         - legal_penetration: "IC_Legal_Scanner"
       sync_barrier: "all_complete"  # 全部完成才进入下一阶段
   
     stage_3_self_correction:
       type: subgraph
       trigger_condition:
         signal: "finance_anomaly_detected"
         source: "IC_Auditor"
       nodes:
         - anomaly_classification
         - legal_deep_scan
         - feedback_merge
       # 自愈完成后通知秘书Agent
   
     stage_4_adversarial:
       type: subgraph
       nodes:
         - anchor_detection
         - adversarial_trigger
         - black_swan_exercise
         - logical_closure
       depends_on:
         - stage_2_parallel_investigation
   
     stage_5_synthesis:
       type: subgraph
       nodes:
         - weighted_scoring
         - report_generation
         - audit_log_consolidation
       depends_on:
         - stage_4_adversarial
         - stage_3_self_correction  # 条件依赖

   global_outputs:
     - investment_recommendation_report
     - audit_log
     - decision_metadata
```

---

## 4. Agent 间消息协议

### 4.1 消息格式

```json
{
  "msg_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "from_agent": "IC_Auditor",
  "to_agent": "IC_Secretary",
  "msg_type": "signal|request|response|report",
  "payload": {
    "signal_name": "anomaly_detected",
    "anomaly_type": "receivables_growth_exceed",
    "severity": "high|medium|low",
    "evidence": ["..."],
    "recommended_action": "legal_deep_scan"
  }
}
```

### 4.2 标准信号定义

| 信号名 | 来源 Agent | 目标 Agent | 说明 |
|--------|-----------|------------|------|
| `project_submitted` | 外部 | IC_Secretary | 新项目接入 |
| `aml_check_complete` | IC_Risk_Controller | IC_Secretary | AML审查完成 |
| `aml_failed` | IC_Risk_Controller | IC_Secretary | AML审查未通过 |
| `valuation_complete` | IC_Auditor | IC_Secretary | 财务估值完成 |
| `sector_analysis_complete` | IC_Sector_Expert | IC_Secretary | 行业分析完成 |
| `policy_analysis_complete` | IC_Strategist | IC_Secretary | 战略对齐完成 |
| `legal_scan_complete` | IC_Legal_Scanner | IC_Secretary | 法务扫描完成 |
| `anomaly_detected` | IC_Auditor | IC_Secretary | 财务异常发现 |
| `self_correction_triggered` | IC_Secretary | IC_Legal_Scanner | 自愈触发 |
| `self_correction_complete` | IC_Legal_Scanner | IC_Secretary | 自愈完成 |
| `adversarial_mode_on` | IC_Chairman | ALL | 红蓝对抗启动 |
| `all_investigation_complete` | IC_Secretary | IC_Chairman | 研判全部完成 |
| `final_report_ready` | IC_Chairman | IC_Secretary | 投决书完成 |

---

## 5. 自愈触发规则

```yaml
self_correction_rules:
  - trigger:
      source: "IC_Auditor"
      signal: "anomaly_detected"
      anomaly_types:
        - "receivables_growth_exceed_revenue"
        - "gross_margin_anomaly"
        - "cash_flow_net_income_divergence"
        - "balance_sheet_reconciliation_failure"
    action:
      target: "IC_Legal_Scanner"
      task: "legal_deep_scan_on_ocr"
      priority: "high"
      sla: "5min"
    
  - trigger:
      source: "IC_Auditor"
      signal: "valuation_uncertainty_high"
    action:
      target: "IC_Sector_Expert"
      task: "peer_comparison_deep_dive"
      priority: "medium"
      sla: "10min"

  - trigger:
      source: "IC_Legal_Scanner"
      signal: "related_party_risk_confirmed"
    action:
      target: "IC_Risk_Controller"
      task: "enhanced_aml_review"
      priority: "high"
      sla: "5min"
```

---

## 6. 并发调度策略

### 6.1 阶段二并发配置

```yaml
stage_2_parallel_investigation:
  mode: "concurrent"
  max_concurrency: 4
  agents:
    - agent: "IC_Auditor"
      workspace: "ic_finance_auditor_workspace"
      estimated_duration: "20min"
      tools:
        - wilcox_valuation_engine
        - dcf_stress_test
    
    - agent: "IC_Sector_Expert"
      workspace: "ic_sector_expert_workspace"
      estimated_duration: "25min"
      tools:
        - analyze_patent_density
        - supply_chain_stress_test
    
    - agent: "IC_Strategist"
      workspace: "ic_strategist_workspace"
      estimated_duration: "20min"
      tools:
        - policy_impact_simulator
        - strategic_alignment_check
    
    - agent: "IC_Legal_Scanner"
      workspace: "ic_legal_scanner_workspace"
      estimated_duration: "30min"
      tools:
        - penetrate_legal_docs
        - check_compliance_2025
      isolation: "physical"  # 物理隔离沙箱
  
  sync_strategy: "all_complete"  # 全部完成才算阶段结束
  timeout: "35min"  # 超时强制进入下一阶段
```

---

## 7. 权重配置

### 7.1 默认专家权重

```yaml
default_weights:
  IC_Auditor: 0.25
  IC_Sector_Expert: 0.25
  IC_Strategist: 0.25
  IC_Legal_Scanner: 0.25
```

### 7.2 赛道自适应权重

```yaml
sector_weights:
  hard_tech:  # 半导体、AI、硬科技
    IC_Auditor: 0.20
    IC_Sector_Expert: 0.45
    IC_Strategist: 0.20
    IC_Legal_Scanner: 0.15
  
  biotech:  # 生物医药
    IC_Auditor: 0.20
    IC_Sector_Expert: 0.35
    IC_Strategist: 0.30
    IC_Legal_Scanner: 0.15
  
  consumer:  # 消费
    IC_Auditor: 0.40
    IC_Sector_Expert: 0.25
    IC_Strategist: 0.20
    IC_Legal_Scanner: 0.15
  
  state_capital:  # 国资主导
    IC_Auditor: 0.20
    IC_Sector_Expert: 0.20
    IC_Strategist: 0.45
    IC_Legal_Scanner: 0.15
```

---

## 8. 审计日志规范

每条操作日志必须包含：

```json
{
  "log_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "agent_id": "IC_Auditor",
  "workspace": "ic_finance_auditor_workspace",
  "action": "tool_call",
  "tool_name": "wilcox_valuation_engine",
  "input": {
    "project_id": "xxx",
    "financial_statements": ["..."]
  },
  "output": {
    "valuation_band": [15.2, 18.7],
    "confidence": 0.92
  },
  "duration_ms": 4523,
  "status": "success|failed|timeout"
}
```

---

## 9. 错误处理与超时策略

| 场景 | 处理策略 |
|------|----------|
| 单个 Agent 超时 | 标记为"未完成"，其他 Agent 继续；主席 Agent 在报告中注明 |
| AML 失败 | 立即终止流程，输出拒绝理由书 |
| 自愈循环超时 | 最多重试 2 次，标记风险升级后强制进入阶段四 |
| 网络/服务异常 | 降级至人工处理模式，保留当前状态快照 |
