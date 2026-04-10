#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discussion Writer - 投委会讨论观点文件系统管理 (V1.0)

功能：
- 管理R1/R2/R3讨论期间的Agent观点（轻量级Markdown文件）
- 实现"新设计"中讨论观点不进Milvus，只写文件系统的机制
- 支持冲突标记、版本追踪
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class DiscussionWriter:
    """
    讨论观点文件系统管理器
    
    目录结构：
    workspace/projects/{project_tag}/
    ├── 10_rounds/
    │   ├── R1/
    │   │   ├── ic_strategist_view.md
    │   │   ├── ic_sector_expert_view.md
    │   │   └── README.md          # 轮次摘要
    │   ├── R2/
    │   └── R3/
    └── 20_conflicts/
        └── conflict_{timestamp}_{topic}.md
    """
    
    def __init__(self, project_tag: str, workspace_root: str = None):
        """
        初始化
        
        Args:
            project_tag: 项目标签
            workspace_root: 工作区根目录（默认~/.openclaw/workspace）
        """
        self.project_tag = project_tag
        
        if workspace_root is None:
            workspace_root = os.path.expanduser("~/.openclaw/workspace")
        
        self.project_dir = os.path.join(workspace_root, "projects", project_tag)
        self.rounds_dir = os.path.join(self.project_dir, "10_rounds")
        self.conflicts_dir = os.path.join(self.project_dir, "20_conflicts")
        
        # 确保目录存在
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录结构存在"""
        for round_num in [1, 2, 3]:
            os.makedirs(os.path.join(self.rounds_dir, f"R{round_num}"), exist_ok=True)
        os.makedirs(self.conflicts_dir, exist_ok=True)
    
    def write_viewpoint(
        self, 
        agent_id: str, 
        round_num: int, 
        content: str,
        metadata: Dict = None
    ) -> str:
        """
        写入Agent观点到指定轮次
        
        Args:
            agent_id: Agent标识
            round_num: 轮次 (1/2/3)
            content: 观点内容（Markdown格式）
            metadata: 元数据（可选）
            
        Returns:
            文件路径
        """
        if round_num not in [1, 2, 3]:
            raise ValueError(f"轮次必须是1/2/3，当前: {round_num}")
        
        # 构建文件路径
        round_dir = os.path.join(self.rounds_dir, f"R{round_num}")
        file_path = os.path.join(round_dir, f"{agent_id}_view.md")
        
        # 构建文件内容（带元数据头）
        file_content = self._build_file_content(
            agent_id=agent_id,
            round_num=round_num,
            content=content,
            metadata=metadata
        )
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        # 更新轮次README
        self._update_round_readme(round_num)
        
        return file_path
    
    def _build_file_content(
        self, 
        agent_id: str, 
        round_num: int, 
        content: str,
        metadata: Dict = None
    ) -> str:
        """构建带元数据头的文件内容"""
        timestamp = datetime.now().isoformat()
        
        header = f"""---
agent_id: {agent_id}
round: R{round_num}
project_tag: {self.project_tag}
created_at: {timestamp}
---

# {self._get_agent_role(agent_id)} - R{round_num}观点

**Agent**: {agent_id}  
**轮次**: R{round_num}  
**时间**: {timestamp}

---

"""
        
        # 如果content已经有标题，移除重复
        content = content.strip()
        if content.startswith('# '):
            lines = content.split('\n', 1)
            if len(lines) > 1:
                content = lines[1].strip()
        
        return header + content + "\n"
    
    def _get_agent_role(self, agent_id: str) -> str:
        """获取Agent角色名称"""
        role_map = {
            "ic_strategist": "战略专家",
            "ic_sector_expert": "行业专家",
            "ic_finance_auditor": "财务专家",
            "ic_legal_scanner": "法律专家",
            "ic_risk_controller": "风控专家",
            "ic_chairman": "主席",
            "ic_master_coordinator": "协调者"
        }
        return role_map.get(agent_id, agent_id)
    
    def read_viewpoint(self, agent_id: str, round_num: int) -> Optional[str]:
        """
        读取指定Agent在指定轮次的观点
        
        Args:
            agent_id: Agent标识
            round_num: 轮次
            
        Returns:
            观点内容，如果不存在返回None
        """
        file_path = os.path.join(
            self.rounds_dir, 
            f"R{round_num}", 
            f"{agent_id}_view.md"
        )
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析元数据和正文
        return self._parse_viewpoint(content)
    
    def _parse_viewpoint(self, content: str) -> Dict:
        """解析观点文件内容"""
        result = {
            "metadata": {},
            "content": content
        }
        
        # 尝试解析YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # 解析元数据
                meta_text = parts[1].strip()
                for line in meta_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result["metadata"][key.strip()] = value.strip()
                
                # 正文是第三部分
                result["content"] = parts[2].strip()
        
        return result
    
    def read_round_views(self, round_num: int) -> List[Dict]:
        """
        读取某一轮次的所有Agent观点
        
        Args:
            round_num: 轮次
            
        Returns:
            观点列表，每项包含agent_id和content
        """
        round_dir = os.path.join(self.rounds_dir, f"R{round_num}")
        
        if not os.path.exists(round_dir):
            return []
        
        views = []
        for filename in os.listdir(round_dir):
            if filename.endswith('_view.md'):
                agent_id = filename.replace('_view.md', '')
                file_path = os.path.join(round_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                parsed = self._parse_viewpoint(content)
                views.append({
                    "agent_id": agent_id,
                    "file_path": file_path,
                    **parsed
                })
        
        # 按Agent ID排序
        views.sort(key=lambda x: x["agent_id"])
        return views
    
    def list_completed_agents(self, round_num: int) -> List[str]:
        """
        列出已完成某轮次的Agent
        
        Args:
            round_num: 轮次
            
        Returns:
            Agent ID列表
        """
        round_dir = os.path.join(self.rounds_dir, f"R{round_num}")
        
        if not os.path.exists(round_dir):
            return []
        
        agents = []
        for filename in os.listdir(round_dir):
            if filename.endswith('_view.md'):
                agent_id = filename.replace('_view.md', '')
                agents.append(agent_id)
        
        return sorted(agents)
    
    def check_round_completion(self, round_num: int, required_agents: List[str] = None) -> Tuple[bool, List[str]]:
        """
        检查某轮次是否完成
        
        Args:
            round_num: 轮次
            required_agents: 必须完成的Agent列表（默认6个专家）
            
        Returns:
            (是否完成, 缺失的Agent列表)
        """
        if required_agents is None:
            required_agents = [
                "ic_strategist",
                "ic_sector_expert", 
                "ic_finance_auditor",
                "ic_legal_scanner",
                "ic_risk_controller"
            ]
        
        completed = set(self.list_completed_agents(round_num))
        required = set(required_agents)
        
        missing = list(required - completed)
        is_complete = len(missing) == 0
        
        return is_complete, sorted(missing)
    
    def build_conflict_marker(
        self, 
        topic: str, 
        agent_a: str, 
        agent_b: str, 
        diff_content: str,
        severity: str = "medium"
    ) -> str:
        """
        创建冲突标记文件
        
        Args:
            topic: 冲突主题
            agent_a: Agent A ID
            agent_b: Agent B ID
            diff_content: 差异内容描述
            severity: 严重度 (low/medium/high)
            
        Returns:
            冲突文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 清理topic作为文件名
        topic_slug = re.sub(r'[^\w\u4e00-\u9fff]+', '_', topic)[:30]
        
        filename = f"conflict_{timestamp}_{topic_slug}.md"
        file_path = os.path.join(self.conflicts_dir, filename)
        
        content = f"""---
topic: {topic}
severity: {severity}
agents: [{agent_a}, {agent_b}]
created_at: {datetime.now().isoformat()}
status: open
---

# 冲突标记: {topic}

**涉及Agent**: {agent_a} vs {agent_b}  
**严重度**: {severity}  
**时间**: {datetime.now().isoformat()}

---

## 差异内容

{diff_content}

---

## 处理状态

- [ ] 等待人类裁决
- [ ] Agent补充论证
- [ ] 已解决

**备注**: 
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _update_round_readme(self, round_num: int):
        """更新轮次README文件"""
        round_dir = os.path.join(self.rounds_dir, f"R{round_num}")
        readme_path = os.path.join(round_dir, "README.md")
        
        views = self.read_round_views(round_num)
        
        content = f"""# R{round_num} 讨论摘要

**项目**: {self.project_tag}  
**轮次**: R{round_num}  
**更新时间**: {datetime.now().isoformat()}

---

## 参与Agent ({len(views)}个)

"""
        
        for view in views:
            agent_id = view["agent_id"]
            role = self._get_agent_role(agent_id)
            meta = view.get("metadata", {})
            created_at = meta.get("created_at", "未知")
            
            content += f"- **{role}** (`{agent_id}`) - {created_at}\n"
        
        content += f"""
---

## 观点文件列表

"""
        
        for view in views:
            agent_id = view["agent_id"]
            filename = f"{agent_id}_view.md"
            content += f"- [{filename}](./{filename})\n"
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def get_project_summary(self) -> Dict:
        """
        获取项目讨论汇总
        
        Returns:
            汇总信息
        """
        summary = {
            "project_tag": self.project_tag,
            "rounds": {},
            "conflicts": []
        }
        
        for round_num in [1, 2, 3]:
            views = self.read_round_views(round_num)
            is_complete, missing = self.check_round_completion(round_num)
            
            summary["rounds"][f"R{round_num}"] = {
                "view_count": len(views),
                "agents": [v["agent_id"] for v in views],
                "is_complete": is_complete,
                "missing_agents": missing
            }
        
        # 读取冲突列表
        if os.path.exists(self.conflicts_dir):
            for filename in os.listdir(self.conflicts_dir):
                if filename.startswith("conflict_") and filename.endswith(".md"):
                    summary["conflicts"].append(filename)
        
        return summary


def main():
    """交互式入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="讨论观点文件系统管理")
    parser.add_argument("--project", required=True, help="项目标签")
    parser.add_argument("--action", required=True, 
                       choices=["write", "read", "list", "check", "summary"],
                       help="操作类型")
    parser.add_argument("--agent", help="Agent ID")
    parser.add_argument("--round", type=int, help="轮次 (1/2/3)")
    parser.add_argument("--content", help="观点内容（write时使用）")
    
    args = parser.parse_args()
    
    writer = DiscussionWriter(project_tag=args.project)
    
    if args.action == "write":
        if not args.agent or not args.round or not args.content:
            print("❌ write操作需要--agent、--round、--content参数")
            return
        
        file_path = writer.write_viewpoint(
            agent_id=args.agent,
            round_num=args.round,
            content=args.content
        )
        print(f"✅ 观点已写入: {file_path}")
    
    elif args.action == "read":
        if not args.agent or not args.round:
            print("❌ read操作需要--agent、--round参数")
            return
        
        result = writer.read_viewpoint(args.agent, args.round)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"⚠️ 未找到观点: {args.agent} R{args.round}")
    
    elif args.action == "list":
        if not args.round:
            print("❌ list操作需要--round参数")
            return
        
        agents = writer.list_completed_agents(args.round)
        print(f"R{args.round} 已完成Agent: {agents}")
    
    elif args.action == "check":
        if not args.round:
            print("❌ check操作需要--round参数")
            return
        
        is_complete, missing = writer.check_round_completion(args.round)
        if is_complete:
            print(f"✅ R{args.round} 已完成")
        else:
            print(f"⏳ R{args.round} 未完成，缺失: {missing}")
    
    elif args.action == "summary":
        summary = writer.get_project_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
