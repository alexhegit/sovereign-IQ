#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIQ 背景知识入库脚本 - OpenAI 兼容接口版 (V1.1)
--------------------------------------------------
使用阿里云 DashScope OpenAI 兼容接口
模型: text-embedding-v4 (2048维)
支持 PDF/DOCX/MD/TXT 格式，含 PDF OCR 视觉补偿

使用示例：
    export DASHSCOPE_API_KEY="sk-xxx"
    
    python3 knowledge_ingestor.py \
        --source /path/to/pdfs \
        --collection ic_strategist_ws \
        --tag macro_strategy_2026 \
        --category background_knowledge
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# 第三方库
from openai import OpenAI
from pypdf import PdfReader
from docx import Document

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("KnowledgeIngestor")

# ============================================================================
# 常量配置
# ============================================================================

# DashScope OpenAI 兼容接口配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBEDDING_MODEL = "qwen3-vl-embedding"
VECTOR_DIM = 1024  # 目标维度

# 分片配置
CHUNK_SIZE = 1500  # 分片大小（字符）
CHUNK_OVERLAP = 300  # 重叠大小
BATCH_SIZE = 10    # DashScope 批次限制

# OCR 配置（可选）
try:
    from pdf2image import convert_from_path
    from rapidocr_onnxruntime import RapidOCR
    OCR_AVAILABLE = True
    OCR_ENGINE = RapidOCR()
except ImportError:
    OCR_AVAILABLE = False
    OCR_ENGINE = None

# ============================================================================
# 主类
# ============================================================================

class KnowledgeIngestor:
    """
    背景知识入库器 - OpenAI 兼容接口版
    
    使用 DashScope text-embedding-v4 生成 2048 维向量
    """
    
    def __init__(
        self,
        collection_name: str,
        project_tag: str = "background",
        category: str = "knowledge",
        api_key: str = None
    ):
        """
        初始化入库器
        
        Args:
            collection_name: 目标 Milvus collection
            project_tag: 项目标签（用于隔离）
            category: 内容分类
            api_key: DashScope API Key
        """
        self.collection_name = collection_name
        self.project_tag = project_tag
        self.category = category
        self.api_key = api_key or DASHSCOPE_API_KEY
        
        if not self.api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或通过 --api-key 传入")
        
        # 初始化 OpenAI 客户端（DashScope 兼容接口）
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=DASHSCOPE_BASE_URL
        )
        
        # 初始化 Milvus
        self._init_milvus()
        
        logger.info(f"✅ 知识入库器初始化完成")
        logger.info(f"   目标库: {collection_name}")
        logger.info(f"   项目标签: {project_tag}")
        logger.info(f"   内容分类: {category}")
        logger.info(f"   向量维度: {VECTOR_DIM}")
    
    def _init_milvus(self):
        """初始化 Milvus 连接"""
        try:
            from pymilvus import connections, Collection, utility
            
            connections.connect("default", host="localhost", port="19530")
            
            if not utility.has_collection(self.collection_name):
                raise RuntimeError(f"Collection {self.collection_name} 不存在")
            
            self.collection = Collection(self.collection_name)
            self.collection.load()
            
            logger.info(f"✅ 已连接 Milvus: {self.collection_name}")
            logger.info(f"   当前实体数: {self.collection.num_entities}")
            
        except Exception as e:
            logger.error(f"❌ Milvus 连接失败: {e}")
            raise
    
    # =====================================================================
    # DashScope Embedding API (OpenAI 兼容接口)
    # =====================================================================
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        调用 DashScope API 生成向量 (OpenAI 兼容接口)
        
        Args:
            texts: 文本列表
            
        Returns:
            2048 维向量列表
        """
        if not texts:
            return []
        
        all_embeddings = []
        
        # 分批处理（DashScope 批次限制为 10）
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            
            # 重试机制
            for retry in range(3):
                try:
                    response = self.client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=batch,
                        dimensions=VECTOR_DIM  # 指定 2048 维
                    )
                    
                    embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(embeddings)
                    
                    logger.debug(f"   批次 {i//BATCH_SIZE + 1} 完成: {len(batch)} 条")
                    break
                    
                except Exception as e:
                    logger.warning(f"   ⚠️ 请求失败 (重试 {retry + 1}/3): {e}")
                    if retry == 2:
                        logger.error(f"   ❌ 批次 {i//BATCH_SIZE + 1} 全部失败: {e}")
                        raise
                    time.sleep((retry + 1) * 2)
        
        return all_embeddings
    
    # =====================================================================
    # 文档解析
    # =====================================================================
    
    def _parse_pdf(self, file_path: str) -> List[Dict]:
        """解析 PDF 文件（含 OCR 视觉补偿）"""
        logger.info(f"   📄 解析 PDF: {os.path.basename(file_path)}")
        
        chunks = []
        reader = PdfReader(file_path)
        
        # 尝试提取文字
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        
        # 如果文字过少，使用 OCR
        if len(text.strip()) < 500 and OCR_AVAILABLE:
            logger.info(f"   🔍 文字量不足，启动 OCR 视觉补偿...")
            chunks = self._parse_pdf_ocr(file_path)
        else:
            chunks = self._chunk_text(text, file_path)
        
        return chunks
    
    def _parse_pdf_ocr(self, file_path: str) -> List[Dict]:
        """OCR 解析扫描件 PDF"""
        chunks = []
        
        try:
            images = convert_from_path(file_path, dpi=150)
            
            for idx, img in enumerate(images):
                result, _ = OCR_ENGINE(img)
                
                if result:
                    page_text = " ".join([line[1] for line in result])
                    chunks.append({
                        "text": page_text,
                        "file": os.path.basename(file_path),
                        "page": idx + 1,
                        "source": "ocr"
                    })
                    logger.info(f"   🔍 第 {idx + 1}/{len(images)} 页 OCR 完成")
                    
        except Exception as e:
            logger.warning(f"   ⚠️ OCR 失败: {e}")
        
        return chunks
    
    def _parse_docx(self, file_path: str) -> List[Dict]:
        """解析 Word 文档"""
        logger.info(f"   📄 解析 Word: {os.path.basename(file_path)}")
        
        doc = Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        
        return self._chunk_text(text, file_path)
    
    def _parse_text(self, file_path: str) -> List[Dict]:
        """解析纯文本文件"""
        logger.info(f"   📄 解析文本: {os.path.basename(file_path)}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        return self._chunk_text(text, file_path)
    
    def _chunk_text(self, text: str, file_path: str) -> List[Dict]:
        """将长文本分片"""
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end]
            
            if len(chunk_text.strip()) > 50:
                chunks.append({
                    "text": chunk_text,
                    "file": os.path.basename(file_path),
                    "chunk_idx": chunk_idx,
                    "source": "text"
                })
                chunk_idx += 1
            
            start += CHUNK_SIZE - CHUNK_OVERLAP
        
        return chunks
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """解析文件（自动识别格式）"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return self._parse_pdf(file_path)
        elif ext == '.docx':
            return self._parse_docx(file_path)
        elif ext in ['.md', '.txt']:
            return self._parse_text(file_path)
        else:
            logger.warning(f"   ⚠️ 不支持的格式: {ext}")
            return []
    
    # =====================================================================
    # 入库流程
    # =====================================================================
    
    def ingest_file(self, file_path: str) -> int:
        """
        入库单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            入库的 chunk 数量
        """
        logger.info(f"\n🔄 处理文件: {file_path}")
        
        # 1. 解析文件
        chunks = self.parse_file(file_path)
        
        if not chunks:
            logger.warning(f"   ⚠️ 未解析到内容")
            return 0
        
        logger.info(f"   📦 解析完成: {len(chunks)} 个分片")
        
        # 2. 生成向量
        texts = [c["text"] for c in chunks]
        logger.info(f"   🔢 正在生成向量...")
        
        vectors = self._get_embeddings(texts)
        
        if len(vectors) != len(chunks):
            logger.error(f"   ❌ 向量化失败: {len(vectors)}/{len(chunks)}")
            return 0
        
        # 3. 组装元数据
        metadata_list = []
        for i, chunk in enumerate(chunks):
            meta = {
                "file_name": chunk["file"],
                "project_tag": self.project_tag,
                "category": self.category,
                "content_type": "background_knowledge",
                "source": chunk.get("source", "text"),
                "page": chunk.get("page", 0),
                "chunk_idx": chunk.get("chunk_idx", i),
                "ingest_time": datetime.now().isoformat(),
                "content_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "vector_dim": VECTOR_DIM
            }
            metadata_list.append(json.dumps(meta, ensure_ascii=False))
        
        # 4. 写入 Milvus
        try:
            self.collection.insert([
                vectors,
                [self.project_tag] * len(vectors),
                metadata_list
            ])
            
            self.collection.flush()
            logger.info(f"   ✅ 入库成功: {len(vectors)} 个向量")
            
            return len(vectors)
            
        except Exception as e:
            logger.error(f"   ❌ Milvus 写入失败: {e}")
            return 0
    
    def ingest_directory(self, dir_path: str, recursive: bool = True) -> Dict:
        """批量入库整个目录"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📥 批量入库: {dir_path}")
        logger.info(f"{'='*60}")
        
        # 收集文件
        files = []
        path = Path(dir_path)
        pattern = "**/*" if recursive else "*"
        
        for ext in ['pdf', 'docx', 'md', 'txt']:
            files.extend(path.glob(f"{pattern}.{ext}"))
        
        files = [str(f) for f in files]
        logger.info(f"📂 找到 {len(files)} 个文件")
        
        # 逐文件处理
        stats = {
            "total_files": len(files),
            "success_files": 0,
            "failed_files": 0,
            "total_chunks": 0
        }
        
        for i, file_path in enumerate(files, 1):
            logger.info(f"\n[{i}/{len(files)}] {file_path}")
            
            try:
                count = self.ingest_file(file_path)
                if count > 0:
                    stats["success_files"] += 1
                    stats["total_chunks"] += count
                else:
                    stats["failed_files"] += 1
            except Exception as e:
                logger.error(f"   ❌ 处理异常: {e}")
                stats["failed_files"] += 1
        
        # 最终统计
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 入库完成")
        logger.info(f"{'='*60}")
        logger.info(f"   总文件: {stats['total_files']}")
        logger.info(f"   成功: {stats['success_files']}")
        logger.info(f"   失败: {stats['failed_files']}")
        logger.info(f"   总向量: {stats['total_chunks']}")
        logger.info(f"   当前库实体数: {self.collection.num_entities}")
        
        return stats
    
    def close(self):
        """关闭连接"""
        try:
            from pymilvus import connections
            connections.disconnect("default")
            logger.info("✅ Milvus 连接已关闭")
        except:
            pass


# ============================================================================
# 命令行入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SIQ 背景知识入库脚本 - OpenAI 兼容接口版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 设置 API Key（必须）
  export DASHSCOPE_API_KEY="sk-xxx"

  # 入库单个 PDF 到战略专家库
  python3 knowledge_ingestor.py \\
      --source /path/to/宏观策略手册.pdf \\
      --collection ic_strategist_ws \\
      --tag macro_strategy \\
      --category methodology

  # 批量入库整个目录到财务专家库
  python3 knowledge_ingestor.py \\
      --source /path/to/财务分析文档/ \\
      --collection ic_finance_auditor_ws \\
      --tag valuation_methods \\
      --category background_knowledge

支持格式: PDF (含OCR), DOCX, MD, TXT
向量维度: 2048 (text-embedding-v4)
        """
    )
    
    parser.add_argument(
        "--source", "-s",
        required=True,
        help="源文件或目录路径"
    )
    
    parser.add_argument(
        "--collection", "-c",
        required=True,
        help="目标 Milvus collection 名称"
    )
    
    parser.add_argument(
        "--tag", "-t",
        default="background",
        help="项目标签（用于数据隔离，默认: background）"
    )
    
    parser.add_argument(
        "--category",
        default="knowledge",
        choices=["knowledge", "methodology", "case_study", "framework"],
        help="内容分类"
    )
    
    parser.add_argument(
        "--api-key",
        default=os.getenv("DASHSCOPE_API_KEY"),
        help="DashScope API Key（默认从环境变量 DASHSCOPE_API_KEY 读取）"
    )
    
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="不递归处理子目录"
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.api_key:
        print("❌ 错误: 请设置 DASHSCOPE_API_KEY 环境变量或通过 --api-key 传入")
        sys.exit(1)
    
    if not os.path.exists(args.source):
        print(f"❌ 错误: 路径不存在: {args.source}")
        sys.exit(1)
    
    # 创建入库器
    ingestor = KnowledgeIngestor(
        collection_name=args.collection,
        project_tag=args.tag,
        category=args.category,
        api_key=args.api_key
    )
    
    try:
        # 执行入库
        if os.path.isfile(args.source):
            count = ingestor.ingest_file(args.source)
            print(f"\n✅ 完成: 入库 {count} 个向量")
        else:
            recursive = not args.no_recursive
            stats = ingestor.ingest_directory(args.source, recursive=recursive)
            
            print(f"\n{'='*60}")
            print("📊 入库统计")
            print(f"{'='*60}")
            print(f"   总文件: {stats['total_files']}")
            print(f"   成功: {stats['success_files']}")
            print(f"   失败: {stats['failed_files']}")
            print(f"   总向量: {stats['total_chunks']}")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        raise
    finally:
        ingestor.close()


if __name__ == "__main__":
    main()
