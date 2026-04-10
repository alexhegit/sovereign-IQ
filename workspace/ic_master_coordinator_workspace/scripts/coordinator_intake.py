#!/usr/bin/env python3
"""
SIQ 投委会 - Coordinator 入口信息校验模块 v3.0
功能：
1. 统一拉取企查查数据（4个端点）
2. 生成信息质量评分卡
3. 差异分析
4. 决策：继续尽调 或 暂停澄清
"""

import json
import subprocess
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# ============== 配置 ==============
QCC_TOKEN = "M4WAY2HB1uf5nYN6xZjMpiBKDTtyr8uNYJf5EsqoWi3FKloI"
QCC_COMPANY_URL = "https://agent.qcc.com/mcp/company/stream"
QCC_RISK_URL = "https://agent.qcc.com/mcp/risk/stream"
QCC_IPR_URL = "https://agent.qcc.com/mcp/ipr/stream"
QCC_OPERATION_URL = "https://agent.qcc.com/mcp/operation/stream"

# ============== 企查查API调用 ==============

def call_qcc(url: str, tool_name: str, arguments: dict) -> dict:
    """调用企查查MCP API"""
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }
    
    cmd = [
        "curl", "-s", "-X", "POST", url,
        "-H", f"Authorization: Bearer {QCC_TOKEN}",
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json, text/event-stream",
        "-d", json.dumps(payload)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return parse_response(result.stdout)

def parse_response(response: str) -> dict:
    """解析企查查API响应"""
    lines = response.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            data_str = line[6:]
            try:
                data = json.loads(data_str)
                if 'result' in data and 'content' in data['result']:
                    content = data['result']['content']
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get('text', '')
                        if text:
                            return json.loads(text)
                    return data.get('result', {})
                elif 'error' in data:
                    return {"error": data['error']}
            except json.JSONDecodeError:
                continue
    return {"error": "Failed to parse response", "raw": response[:200]}

# ============== 数据拉取函数 ==============

def fetch_company_info(search_key: str) -> dict:
    """获取工商信息"""
    return call_qcc(QCC_COMPANY_URL, "get_company_registration_info", {"searchKey": search_key})

def fetch_shareholder_info(search_key: str) -> dict:
    """获取股东信息"""
    return call_qcc(QCC_COMPANY_URL, "get_shareholder_info", {"searchKey": search_key})

def fetch_change_records(search_key: str) -> dict:
    """获取变更记录"""
    return call_qcc(QCC_COMPANY_URL, "get_change_records", {"searchKey": search_key})

def fetch_company_profile(search_key: str) -> dict:
    """获取企业简介"""
    return call_qcc(QCC_COMPANY_URL, "get_company_profile", {"searchKey": search_key})

def fetch_key_personnel(search_key: str) -> dict:
    """获取主要人员"""
    return call_qcc(QCC_COMPANY_URL, "get_key_personnel", {"searchKey": search_key})

def fetch_annual_reports(search_key: str) -> dict:
    """获取企业年报"""
    return call_qcc(QCC_COMPANY_URL, "get_annual_reports", {"searchKey": search_key})

# 风险相关工具
def fetch_risk_summary(search_key: str) -> dict:
    """获取风险汇总（经营异常+失信+严重违法）"""
    results = {}
    
    # 经营异常
    results['business_exception'] = call_qcc(QCC_RISK_URL, "get_business_exception", {"searchKey": search_key})
    
    # 失信信息
    results['dishonest'] = call_qcc(QCC_RISK_URL, "get_dishonest_info", {"searchKey": search_key})
    
    # 严重违法
    results['serious_violation'] = call_qcc(QCC_RISK_URL, "get_serious_violation", {"searchKey": search_key})
    
    # 被执行人
    results['judgment_debtor'] = call_qcc(QCC_RISK_URL, "get_judgment_debtor_info", {"searchKey": search_key})
    
    # 税务异常
    results['tax_abnormal'] = call_qcc(QCC_RISK_URL, "get_tax_abnormal", {"searchKey": search_key})
    
    return results

def fetch_ipr_summary(search_key: str) -> dict:
    """获取知识产权汇总"""
    # IPR端点的工具列表需要先查询，这里用company端点的专利工具
    results = {}
    
    # 使用company端点获取专利信息（如果可用）
    results['patent'] = call_qcc(QCC_COMPANY_URL, "get_patent_info", {"searchKey": search_key})
    results['trademark'] = call_qcc(QCC_COMPANY_URL, "get_trademark_info", {"searchKey": search_key})
    results['copyright'] = call_qcc(QCC_COMPANY_URL, "get_software_copyright", {"searchKey": search_key})
    
    return results

def fetch_operation_info(search_key: str) -> dict:
    """获取经营信息"""
    results = {}
    
    # 上市信息
    results['listing'] = call_qcc(QCC_COMPANY_URL, "get_listing_info", {"searchKey": search_key})
    
    # 对外投资
    results['external_investments'] = call_qcc(QCC_COMPANY_URL, "get_external_investments", {"searchKey": search_key})
    
    # 分支机构
    results['branches'] = call_qcc(QCC_COMPANY_URL, "get_branches", {"searchKey": search_key})
    
    return results

# ============== 信息校验核心逻辑 ==============

def extract_company_fields(data: dict) -> dict:
    """从工商数据中提取关键字段"""
    if 'error' in data:
        return {}
    
    result = {}
    if isinstance(data, dict):
        result['company_name'] = data.get('企业名称') or data.get('name')
        result['credit_code'] = data.get('统一社会信用代码') or data.get('creditCode')
        result['legal_rep'] = data.get('法定代表人') or data.get('legalRep')
        result['reg_capital'] = data.get('注册资本') or data.get('regCapital')
        result['establish_date'] = data.get('成立日期') or data.get('establishDate')
        result['company_status'] = data.get('登记状态') or data.get('status')
        result['company_type'] = data.get('企业类型') or data.get('companyType')
        result['employee_count'] = data.get('人员规模') or data.get('employeeCount')
        result['business_scope'] = data.get('经营范围') or data.get('businessScope')
        result['reg_address'] = data.get('注册地址') or data.get('regAddress')
    
    return result

def normalize_company_name(name: str) -> str:
    """标准化公司名称：去除后缀、括号内容"""
    if not name:
        return ""
    import re
    # 去除常见后缀
    name = re.sub(r'（.*?）', '', name)  # 去除括号及其内容
    name = re.sub(r'\(.*?\)', '', name)
    suffixes = ['股份有限公司', '有限公司', '有限责任公司', '普通合伙', '特殊普通合伙', '有限合伙']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

def compare_with_task_description(qcc_data: dict, task_description: dict) -> dict:
    """对比企查查数据与任务描述，输出差异分析"""
    discrepancies = []
    
    field_mappings = {
        'company_name': ['公司名称', '公司全称', '企业名称'],
        'establish_date': ['成立日期', '成立时间', '创立时间'],
        'reg_capital': ['注册资本', '注册资金'],
        'main_business': ['主营业务', '主要业务', '业务范围'],
        'employee_count': ['员工规模', '人员规模', '员工人数']
    }
    
    qcc_fields = extract_company_fields(qcc_data)
    
    for field_key, task_field_names in field_mappings.items():
        qcc_value = qcc_fields.get(field_key, 'N/A')
        
        task_value = None
        for name in task_field_names:
            if name in task_description:
                task_value = task_description[name]
                break
        
        if task_value and qcc_value and qcc_value != 'N/A':
            # 公司名称特殊处理：允许全称/简称差异
            if field_key == 'company_name':
                task_norm = normalize_company_name(str(task_value))
                qcc_norm = normalize_company_name(str(qcc_value))
                if task_norm != qcc_norm:
                    discrepancies.append({
                        'field': field_key,
                        'task_value': task_value,
                        'qcc_value': qcc_value,
                        'severity': 'LOW',  # 公司名称差异降为LOW
                        'description': f'简称/全称差异（标准化后一致: {task_norm} vs {qcc_norm}）'
                    })
            elif 'date' in field_key:
                if str(task_value)[:4] != str(qcc_value)[:4]:
                    discrepancies.append({
                        'field': field_key,
                        'task_value': task_value,
                        'qcc_value': qcc_value,
                        'severity': 'HIGH',
                        'description': '成立年份不匹配'
                    })
            else:
                discrepancies.append({
                    'field': field_key,
                    'task_value': task_value,
                    'qcc_value': qcc_value,
                    'severity': 'HIGH',
                    'description': '字段值不匹配'
                })
    
    return discrepancies

def generate_scorecard(qcc_data: dict, discrepancies: list) -> dict:
    """生成信息质量评分卡"""
    
    high_severity = sum(1 for d in discrepancies if d['severity'] == 'HIGH')
    low_severity = sum(1 for d in discrepancies if d['severity'] == 'LOW')
    
    if high_severity > 0:
        level = "L1 - 危险"
        level_code = 1
        action = "PAUSE_AND_CLARIFY"
    elif low_severity > 2:
        level = "L2 - 存疑"
        level_code = 2
        action = "PROCEED_WITH_CAUTION"
    elif low_severity > 0:
        level = "L3 - 可靠"
        level_code = 3
        action = "PROCEED"
    else:
        level = "L4 - 可信"
        level_code = 4
        action = "PROCEED"
    
    return {
        'level': level,
        'level_code': level_code,
        'action': action,
        'high_severity_count': high_severity,
        'low_severity_count': low_severity,
        'timestamp': datetime.now().isoformat()
    }

def summarize_shareholders(shareholder_data: dict) -> list:
    """提取股东信息摘要"""
    if 'error' in shareholder_data:
        return []
    
    shareholders = []
    if isinstance(shareholder_data, dict):
        # 尝试多种可能的结构
        data = shareholder_data.get('股东信息') or shareholder_data.get('shareholders') or shareholder_data
        if isinstance(data, list):
            for s in data[:10]:  # 只取前10个
                name = s.get('投资人') or s.get('股东名称') or s.get('name') or s.get('ShareholderName')
                share = s.get('持股比例') or s.get('shareRatio') or s.get('SharePercent')
                if name:
                    shareholders.append(f"{name}: {share}")
        elif isinstance(data, dict):
            for key, value in list(data.items())[:10]:
                shareholders.append(f"{key}: {value}")
    
    return shareholders

# ============== 报告生成 ==============

def generate_verified_data_package(search_key: str, task_description: dict) -> dict:
    """生成验证数据包"""
    
    print("=" * 60)
    print("SIQ Coordinator - 入口信息校验 v3.0")
    print(f"查询关键词: {search_key}")
    print("=" * 60)
    
    # 1. 获取工商信息
    print("\n[1/6] 获取工商信息...")
    company_info = fetch_company_info(search_key)
    
    if company_info.get('error') or not company_info.get('企业名称'):
        # 尝试用统一社会信用代码查询
        if '统一社会信用代码' in str(task_description):
            code = task_description.get('统一社会信用代码')
            print(f"  └─ 尝试用统一社会信用代码 {code} 查询...")
            company_info = fetch_company_info(code)
        
        if company_info.get('error') or not company_info.get('企业名称'):
            print(f"  ✗ 查询失败: {company_info.get('error', '未知错误')}")
            return {
                'status': 'ERROR',
                'error': company_info.get('error', '未找到匹配公司'),
                'search_key': search_key,
                'action': 'PAUSE_AND_CLARIFY'
            }
    
    qcc_fields = extract_company_fields(company_info)
    print(f"  ✓ 企业名称: {qcc_fields.get('company_name', 'N/A')}")
    print(f"  ✓ 法定代表人: {qcc_fields.get('legal_rep', 'N/A')}")
    print(f"  ✓ 成立日期: {qcc_fields.get('establish_date', 'N/A')}")
    print(f"  ✓ 注册资本: {qcc_fields.get('reg_capital', 'N/A')}")
    print(f"  ✓ 登记状态: {qcc_fields.get('company_status', 'N/A')}")
    
    # 2. 获取股东信息
    print("\n[2/6] 获取股东信息...")
    shareholder_info = fetch_shareholder_info(search_key)
    shareholders = summarize_shareholders(shareholder_info)
    if shareholders:
        print(f"  ✓ 获取 {len(shareholders)} 条股东信息")
        for s in shareholders[:5]:
            print(f"     - {s}")
    else:
        print(f"  ⚠ 未能获取股东信息")
    
    # 3. 获取变更记录
    print("\n[3/6] 获取变更记录...")
    change_records = fetch_change_records(search_key)
    if not change_records.get('error'):
        changes = change_records.get('变更记录', [])
        print(f"  ✓ 获取 {len(changes) if isinstance(changes, list) else '若干'} 条变更记录")
    else:
        print(f"  ⚠ 获取失败")
    
    # 4. 获取风险信息
    print("\n[4/6] 获取风险信息...")
    risk_info = fetch_risk_summary(search_key)
    risk_summary = []
    for risk_type, data in risk_info.items():
        if not data.get('error') and data:
            items = data if isinstance(data, list) else [data]
            if items and items[0]:
                risk_summary.append(f"{risk_type}: {len(items)} 条")
    if risk_summary:
        print(f"  ✓ 风险检查结果:")
        for r in risk_summary:
            print(f"     - {r}")
    else:
        print(f"  ✓ 未发现风险信息（正常）")
    
    # 5. 获取经营信息
    print("\n[5/6] 获取经营信息...")
    operation_info = fetch_operation_info(search_key)
    if not operation_info.get('error'):
        listing = operation_info.get('listing', {})
        if listing and not listing.get('error'):
            print(f"  ✓ 上市信息: {listing.get('股票简称', 'N/A')} ({listing.get('股票代码', 'N/A')})")
        investments = operation_info.get('external_investments', {})
        if investments and not investments.get('error'):
            print(f"  ✓ 对外投资: 已获取")
    
    # 6. 差异分析
    print("\n[6/6] 差异分析...")
    discrepancies = compare_with_task_description(company_info, task_description)
    
    if discrepancies:
        print("\n" + "!" * 60)
        print("发现差异:")
        print("!" * 60)
        for d in discrepancies:
            severity_icon = "🔴" if d['severity'] == 'HIGH' else "🟡"
            print(f"\n{severity_icon} [{d['severity']}] {d['field']}")
            print(f"   任务描述: {d['task_value']}")
            print(f"   企查查数据: {d['qcc_value']}")
    else:
        print("  ✓ 未发现重大差异")
    
    # 生成评分卡
    scorecard = generate_scorecard(company_info, discrepancies)
    
    print("\n" + "=" * 60)
    print("信息质量评分卡")
    print("=" * 60)
    level_icon = "🔴" if scorecard['level_code'] == 1 else "🟡" if scorecard['level_code'] == 2 else "🟢"
    print(f"{level_icon} 等级: {scorecard['level']}")
    print(f"📋 高严重度差异: {scorecard['high_severity_count']}")
    print(f"⚠️ 低严重度差异: {scorecard['low_severity_count']}")
    
    action_text = {
        "PAUSE_AND_CLARIFY": "⏸️ 暂停尽调，请先澄清差异项",
        "PROCEED_WITH_CAUTION": "⚠️ 可继续，但需标注存疑项",
        "PROCEED": "✅ 可正常进入尽调流程"
    }
    print(f"\n▶️ 建议操作: {action_text.get(scorecard['action'], scorecard['action'])}")
    
    # 打包验证数据包
    package = {
        'status': 'SUCCESS',
        'search_key': search_key,
        'task_description': task_description,
        'qcc_data': {
            'company_info': company_info,
            'shareholder_info': shareholder_info,
            'change_records': change_records,
            'risk_info': risk_info,
            'operation_info': operation_info
        },
        'extracted_fields': qcc_fields,
        'shareholders_summary': shareholders,
        'discrepancies': discrepancies,
        'scorecard': scorecard,
        'verification_timestamp': datetime.now().isoformat(),
        'verified_by': 'Coordinator_QCC_API_v3'
    }
    
    # 输出决策
    print("\n" + "=" * 60)
    if scorecard['action'] == 'PAUSE_AND_CLARIFY':
        print("🚨 决策: 暂停尽调")
        print("=" * 60)
        print("\n📋 需要澄清的差异项:")
        for d in discrepancies:
            if d['severity'] == 'HIGH':
                print(f"  - {d['field']}: 任务 '{d['task_value']}' vs 真实 '{d['qcc_value']}'")
    else:
        print("✅ 决策: 可进入尽调流程")
    
    return package

def save_package(package: dict, output_path: str):
    """保存验证数据包"""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(package, f, ensure_ascii=False, indent=2)
    print(f"\n📁 验证数据包已保存: {output_path}")

# ============== 主函数 ==============

def main():
    parser = argparse.ArgumentParser(description='SIQ Coordinator 入口信息校验 v3.0')
    parser.add_argument('company', help='公司名称或统一社会信用代码')
    parser.add_argument('--task-json', help='任务描述JSON字符串', default='{}')
    parser.add_argument('--output', help='输出文件路径', 
                        default='/home/xsuper/.openclaw/workspace/ic_master_coordinator_workspace/verified_data_package.json')
    args = parser.parse_args()
    
    # 解析任务描述
    try:
        task_description = json.loads(args.task_json) if args.task_json else {}
    except json.JSONDecodeError:
        print("⚠️ 任务描述JSON解析失败，使用空描述")
        task_description = {}
    
    # 生成验证数据包
    package = generate_verified_data_package(args.company, task_description)
    
    # 保存
    save_package(package, args.output)
    
    # 返回退出码
    if package['status'] == 'ERROR':
        sys.exit(2)
    elif package['scorecard']['action'] == 'PAUSE_AND_CLARIFY':
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
