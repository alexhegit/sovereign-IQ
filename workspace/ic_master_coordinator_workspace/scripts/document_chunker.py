#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文档分块处理器 - Document Chunker for SIQ
分块大小：1500字符，重叠：300字符（20%）
用于处理500页PDF底稿，生成向量化所需的chunks
"""

import json
import os
import re
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import sys


class DocumentChunker:
    """
    文档分块器
    
    配置（从config/agent_retrieval_config.json读取）：
    - chunk_size: 1500字符
    - overlap: 300字符（20%）
    - metadata: 章节、主题、数据类型、页码
    """
    
    def __init__(self, config_path: str = None):
        """初始化分块器"""
        if config_path is None:
            config_path = os.path.expanduser(
                "~/.openclaw/workspace/ic_master_coordinator_workspace/config/agent_retrieval_config.json"
            )
        
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.chunk_config = config.get('chunk_config', {})
        self.chunk_size = self.chunk_config.get('chunk_size', 1500)
        self.overlap = self.chunk_config.get('overlap', 300)
        self.overlap_percentage = self.chunk_config.get('overlap_percentage', 0.2)
        
        print(f"✅ 分块器初始化完成")
        print(f"   分块大小: {self.chunk_size}字符")
        print(f"   重叠: {self.overlap}字符 ({self.overlap_percentage*100}%)")
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        将文本分块
        
        Args:
            text: 原始文本
            metadata: 文档元数据（章节、页码等）
        
        Returns:
            chunks: [{"id": "...", "text": "...", "metadata": {...}}]
        """
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        text_length = len(text)
        
        print(f"📄 开始分块，文本总长度: {text_length}字符")
        
        while start < text_length:
            # 计算结束位置
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句子边界截断
            if end < text_length:
                # 向后查找最近的句子边界（句号、分号、换行）
                search_end = min(end + 200, text_length)
                next_break = self._find_sentence_boundary(text[end:search_end])
                
                if next_break != -1:
                    end = end + next_break
            else:
                end = text_length
            
            # 提取chunk文本
            chunk_text = text[start:end].strip()
            
            if chunk_text and len(chunk_text) > 50:  # 避免空块或过短块
                # 生成chunk ID
                chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                
                chunk = {
                    "id": f"chunk_{chunk_id:04d}_{chunk_hash}",
                    "text": chunk_text,
                    "metadata": {
                        **(metadata or {}),
                        "char_start": start,
                        "char_end": end,
                        "char_count": len(chunk_text),
                        "chunk_index": chunk_id,
                        "created_at": datetime.now().isoformat()
                    }
                }
                chunks.append(chunk)
                chunk_id += 1
            
            # 移动起始位置（考虑重叠）
            start = end - self.overlap
            
            # 防止死循环
            if start >= end:
                break
        
        print(f"✅ 分块完成: {len(chunks)}个chunks")
        return chunks
    
    def _find_sentence_boundary(self, text: str) -> int:
        """
        查找句子边界位置
        
        优先级：
        1. 句号、分号、换行
        2. 逗号（如果距离合适）
        3. 空格
        """
        # 优先查找句子结束符
        for char in ['。', '；', '\n', '.', ';', '？', '！']:
            pos = text.find(char)
            if pos != -1 and pos < 200:  # 在合理范围内
                return pos + 1
        
        # 其次查找逗号
        pos = text.find('，')
        if pos != -1 and pos < 100:
            return pos + 1
        
        # 最后查找空格
        pos = text.find(' ')
        if pos != -1 and pos < 50:
            return pos + 1
        
        return -1
    
    def extract_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        从PDF提取文本并分块
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            chunks with page metadata
        """
        print(f"📄 正在处理PDF: {pdf_path}")
        
        try:
            import pdfplumber
        except ImportError:
            print("❌ 请先安装pdfplumber: pip install pdfplumber")
            return []
        
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}")
            return []
        
        all_chunks = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"📊 PDF总页数: {total_pages}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                # 提取页面文本
                text = page.extract_text()
                
                if text and len(text.strip()) > 0:
                    # 为每页分块
                    page_chunks = self.chunk_text(
                        text,
                        metadata={
                            "page": page_num,
                            "total_pages": total_pages,
                            "source_type": "pdf",
                            "source_file": os.path.basename(pdf_path)
                        }
                    )
                    all_chunks.extend(page_chunks)
                
                # 进度显示
                if page_num % 50 == 0 or page_num == total_pages:
                    print(f"   处理进度: {page_num}/{total_pages}页")
        
        print(f"✅ PDF处理完成: {len(all_chunks)}个chunks")
        return all_chunks
    
    def add_section_metadata(self, chunks: List[Dict], toc: List[Dict]) -> List[Dict]:
        """
        根据目录添加章节元数据
        
        Args:
            chunks: 分块列表
            toc: 目录结构 [{"title": "第一章", "page": 1, "topic": "概述", "data_type": "text"}]
        
        Returns:
            更新metadata后的chunks
        """
        print(f"📑 添加章节元数据...")
        
        for chunk in chunks:
            page = chunk["metadata"].get("page", 0)
            
            # 查找所属章节（基于页码）
            current_section = None
            for section in toc:
                if page >= section["page"]:
                    current_section = section
            
            if current_section:
                chunk["metadata"]["section"] = current_section.get("title", "未知章节")
                chunk["metadata"]["topic"] = current_section.get("topic", "general")
                chunk["metadata"]["data_type"] = current_section.get("data_type", "text")
            else:
                chunk["metadata"]["section"] = "正文"
                chunk["metadata"]["topic"] = "general"
                chunk["metadata"]["data_type"] = "text"
        
        print(f"✅ 章节元数据添加完成")
        return chunks
    
    def detect_data_type(self, text: str) -> str:
        """
        自动检测数据类型
        
        Returns:
            数据类型: financial/legal/technical/market/general
        """
        text_lower = text.lower()
        
        # 财务指标关键词
        financial_keywords = ['收入', '利润', '成本', '现金流', '估值', '融资', '财务', '毛利率', '净利率', 'LTV', 'CAC']
        # 法律关键词
        legal_keywords = ['股权', '专利', '诉讼', '合同', '合规', '条款', '知识产权', '商标', '著作权']
        # 技术关键词
        technical_keywords = ['技术', '专利', '研发', '算法', '产品', '核心', '壁垒', '创新']
        # 市场关键词
        market_keywords = ['市场', '客户', '竞争', '行业', '增长', '规模', '份额', 'TAM', 'SAM', 'SOM']
        
        scores = {
            'financial': sum(1 for k in financial_keywords if k in text_lower),
            'legal': sum(1 for k in legal_keywords if k in text_lower),
            'technical': sum(1 for k in technical_keywords if k in text_lower),
            'market': sum(1 for k in market_keywords if k in text_lower)
        }
        
        if max(scores.values()) == 0:
            return 'general'
        
        return max(scores, key=scores.get)
    
    def save_chunks(self, chunks: List[Dict], output_path: str):
        """
        保存chunks到JSON文件
        
        Args:
            chunks: 分块列表
            output_path: 输出路径
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 准备输出数据
        output_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "chunk_count": len(chunks),
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
                "tool": "document_chunker.py",
                "version": "1.0"
            },
            "chunks": chunks
        }
        
        # 保存为JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Chunks已保存: {output_path}")
        print(f"   总数: {len(chunks)}个chunks")
    
    def process_project_draft(self, pdf_path: str, project_tag: str, output_dir: str = None) -> str:
        """
        处理项目底稿（完整流程）
        
        Args:
            pdf_path: PDF文件路径
            project_tag: 项目标签
            output_dir: 输出目录
        
        Returns:
            输出文件路径
        """
        if output_dir is None:
            output_dir = os.path.expanduser(
                f"~/.openclaw/workspace/projects/{project_tag}/01_chunks"
            )
        
        print(f"\n{'='*60}")
        print(f"🚀 开始处理项目底稿")
        print(f"{'='*60}")
        print(f"项目: {project_tag}")
        print(f"PDF: {pdf_path}")
        print(f"输出: {output_dir}")
        print(f"{'='*60}\n")
        
        # 1. 从PDF提取并分块
        chunks = self.extract_from_pdf(pdf_path)
        
        if not chunks:
            print("❌ 未提取到有效内容")
            return None
        
        # 2. 自动检测数据类型
        print("\n🔍 自动检测数据类型...")
        for chunk in chunks:
            chunk["metadata"]["auto_data_type"] = self.detect_data_type(chunk["text"])
        
        # 3. 保存chunks
        output_path = os.path.join(output_dir, f"{project_tag}_chunks.json")
        self.save_chunks(chunks, output_path)
        
        # 4. 生成统计报告
        self._generate_stats(chunks, output_dir, project_tag)
        
        print(f"\n{'='*60}")
        print(f"✅ 项目底稿处理完成")
        print(f"{'='*60}\n")
        
        return output_path
    
    def _generate_stats(self, chunks: List[Dict], output_dir: str, project_tag: str):
        """生成统计报告"""
        stats = {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(c["metadata"]["char_count"] for c in chunks) / len(chunks) if chunks else 0,
            "data_type_distribution": {},
            "page_coverage": len(set(c["metadata"].get("page", 0) for c in chunks))
        }
        
        # 数据类型分布
        for chunk in chunks:
            data_type = chunk["metadata"].get("auto_data_type", "general")
            stats["data_type_distribution"][data_type] = stats["data_type_distribution"].get(data_type, 0) + 1
        
        # 保存统计
        stats_path = os.path.join(output_dir, f"{project_tag}_chunk_stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 分块统计:")
        print(f"   总chunks: {stats['total_chunks']}")
        print(f"   平均大小: {stats['avg_chunk_size']:.0f}字符")
        print(f"   覆盖页数: {stats['page_coverage']}")
        print(f"   数据类型分布: {stats['data_type_distribution']}")


# 使用示例
if __name__ == "__main__":
    chunker = DocumentChunker()
    
    # 示例1：直接分块文本
    test_text = """
    宇树科技（Unitree）成立于2016年，是一家专注于高性能四足机器人研发、
    生产和销售的高科技企业。公司总部位于杭州，核心团队来自上海交大、浙大等
    知名高校。
    
    公司核心产品包括消费级四足机器人Go1、专业级四足机器人Go2以及行业级
    四足机器人B2等系列产品。其中Go1售价1.6万元起，面向消费娱乐市场；
    Go2面向教育和开发者市场；B2面向行业应用市场。
    
    技术方面，宇树科技自主研发了高扭矩密度关节电机、高性能运动控制算法、
    多传感器融合系统等核心技术。公司已申请专利超过100项，其中发明专利占比
    超过60%。
    """ * 50  # 模拟长文本
    
    print("\n" + "="*60)
    print("测试文本分块")
    print("="*60)
    
    chunks = chunker.chunk_text(test_text, metadata={"source": "test"})
    
    print(f"\n生成的chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk['id']}")
        print(f"  长度: {chunk['metadata']['char_count']}字符")
        print(f"  预览: {chunk['text'][:80]}...")
    
    # 示例2：处理PDF（需要实际PDF文件）
    # pdf_path = "/path/to/底稿.pdf"
    # chunker.process_project_draft(pdf_path, "YUSHU_2026")