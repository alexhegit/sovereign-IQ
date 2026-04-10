#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sovereign-IQ Project Ingestor - 人类底稿入库脚本 (V1.0)
---------------------------------------------------------
功能：供人类用户将项目底稿（PDF/DOCX/MD/TXT）手动入库至协同共享库

设计原则：
1. 人类审核优先：底稿经过人工确认后才入库，确保数据质量
2. 项目标签隔离：通过 project_tag 实现项目级数据隔离
3. 状态机追踪：通过 incoming/processed/failed 目录实现文件状态物理追踪
4. 断点续传：基于本地 JSON 审计文件防止重复入库

使用流程：
1. 人类将待入库底稿放入 incoming 目录
2. 运行本脚本，输入项目标签
3. 脚本解析文件、生成向量、入库至 ic_collaboration_shared_ws
4. 文件自动移动至 processed 或 failed 目录
"""

import os
import sys
import json
import time
import logging
import shutil
import base64
from datetime import datetime
from typing import List, Dict, Any, Set

# 第三方库
from pypdf import PdfReader
from docx import Document
from pdf2image import convert_from_path
import numpy as np
from openai import OpenAI
from pymilvus import connections, Collection, utility

# 🛡️ 兼容配置
try:
    from rapidocr_onnxruntime import RapidOCR
    OCR_ENGINE = RapidOCR()
except ImportError:
    OCR_ENGINE = None
    logging.warning("⚠️ RapidOCR 未安装，扫描件将无法进行视觉补偿解析")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("ProjectIngestor")

# ============================================================================
# 常量配置
# ============================================================================

SHARED_COLLECTION = "ic_collaboration_shared_ws"  # 协同共享库
VECTOR_DIM = 1024  # Qwen3-VL-Embedding-2B 向量维度
CHUNK_SIZE = 800   # 文本分片大小
BATCH_SIZE = 8     # 向量化批次大小
EMBEDDING_API = "http://127.0.0.1:11434/v1"  # Ollama 向量化服务地址
EMBEDDING_MODEL = "qwen3-vl-embedding"

# 状态目录
STATE_INCOMING = "incoming"
STATE_PROCESSED = "processed"
STATE_FAILED = "failed"

# ============================================================================
# 主类
# ============================================================================

class ProjectIngestor:
    """
    项目底稿入库器
    
    职责：
    1. 解析多种格式的底稿文件（MD/TXT/PDF/DOCX）
    2. 生成分片并调用向量化接口
    3. 写入协同共享库 ic_collaboration_shared_ws
    4. 管理文件状态（incoming -> processed/failed）
    """
    
    def __init__(self, base_url: str = EMBEDDING_API):
        """
        初始化入库器
        
        Args:
            base_url: Qwen3-VL-Embedding 服务地址
        """
        self.base_url = base_url
        self.vector_dim = VECTOR_DIM
        self.chunk_size = CHUNK_SIZE
        self.batch_size = BATCH_SIZE
        
        # 初始化 OpenAI 兼容客户端（对接本地向量化服务）
        self.client = OpenAI(api_key="EMPTY", base_url=base_url)
        
        # 初始化数据库连接
        self._init_milvus()
        
        # 进度日志路径（用于断点续传）
        self.progress_log = f".ingest_progress_{SHARED_COLLECTION}.json"
    
    def _init_milvus(self):
        """建立与 Milvus 的连接并加载共享库"""
        try:
            connections.connect("default", host="localhost", port="19530")
            
            if not utility.has_collection(SHARED_COLLECTION):
                raise RuntimeError(
                    f"协同共享库 {SHARED_COLLECTION} 不存在。"
                    "请先通过 env_setup.py 初始化数据库。"
                )
            
            self.collection = Collection(SHARED_COLLECTION)
            self.collection.load()
            logger.info(f"✅ 已挂载协同共享库: {SHARED_COLLECTION}")
            logger.info(f"   当前实体数: {self.collection.num_entities}")
            
        except Exception as e:
            logger.error(f"❌ Milvus 连接失败: {e}")
            sys.exit(1)
    
    # =========================================================================
    # 向量化接口
    # =========================================================================
    
    def _get_embeddings(self, batch_payload: List[Dict]) -> List[List[float]]:
        """
        调用 Qwen3-VL 原生多模态接口生成向量
        
        Args:
            batch_payload: [{"text": "..."}] 或 [{"image": "base64..."}]
            
        Returns:
            向量列表，维度为 VECTOR_DIM
        """
        formatted = []
        for item in batch_payload:
            if "text" in item:
                formatted.append({"type": "text", "text": item["text"]})
            elif "image" in item:
                formatted.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{item['image']}"}
                })
        
        # 调用向量化服务，含重试机制
        for retry in range(3):
            try:
                response = self.client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=formatted,
                    timeout=60.0
                )
                return [d.embedding for d in response.data]
            except Exception as e:
                logger.warning(f"⚠️ 向量化请求失败 (重试 {retry + 1}/3): {e}")
                time.sleep((retry + 1) * 2)
        
        logger.error(f"❌ 向量化请求全部失败，跳过此批次")
        return []
    
    # =========================================================================
    # 文件解析逻辑
    # =========================================================================
    
    def _parse_file(self, file_path: str) -> List[Dict]:
        """
        解析底稿文件并分片
        
        支持格式：
        - 纯文本：MD, TXT
        - Word：DOCX
        - PDF：文字版 或 扫描件（走 OCR 视觉补偿）
        
        Args:
            file_path: 文件绝对路径
            
        Returns:
            分片列表，每项包含 text 或 image
        """
        ext = os.path.splitext(file_path)[1].lower()
        chunks = []
        
        try:
            # ----------------------------------------------------------
            # 1. 纯文本类：直接读取并分片
            # ----------------------------------------------------------
            if ext in ['.md', '.txt']:
                logger.info(f"   📄 解析文本文件: {os.path.basename(file_path)}")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                chunks = self._chunk_text(text)
            
            # ----------------------------------------------------------
            # 2. Word 文档：提取段落文本
            # ----------------------------------------------------------
            elif ext == '.docx':
                logger.info(f"   📄 解析 Word 文档: {os.path.basename(file_path)}")
                doc = Document(file_path)
                full_text = "\n".join([p.text for p in doc.paragraphs])
                chunks = self._chunk_text(full_text)
            
            # ----------------------------------------------------------
            # 3. PDF：优先提取文字，文字不足时走 OCR 视觉补偿
            # ----------------------------------------------------------
            elif ext == '.pdf':
                logger.info(f"   📄 解析 PDF: {os.path.basename(file_path)}")
                reader = PdfReader(file_path)
                text = "".join([p.extract_text() or "" for p in reader.pages])
                
                # 文字极少（<100字符），判定为扫描件，执行视觉解析
                if len(text.strip()) < 100:
                    if OCR_ENGINE:
                        logger.info(f"   🔍 检测为扫描件，启动 RapidOCR 视觉补偿...")
                        chunks = self._parse_pdf_vision(file_path)
                    else:
                        logger.warning(f"   ⚠️ 文字过少且无 OCR 引擎，仅入库文字残片")
                        chunks = self._chunk_text(text) if text.strip() else []
                else:
                    chunks = self._chunk_text(text)
            
            else:
                logger.warning(f"   ⚠️ 不支持的文件格式: {ext}，已跳过")
                
        except Exception as e:
            logger.error(f"   ❌ 文件解析异常: {e}")
        
        return chunks
    
    def _chunk_text(self, text: str) -> List[Dict]:
        """
        将长文本分片
        
        Args:
            text: 原始文本
            
        Returns:
            分片列表 [{"text": "..."}]
        """
        return [
            {"text": text[i:i + self.chunk_size]}
            for i in range(0, len(text), self.chunk_size)
        ]
    
    def _parse_pdf_vision(self, file_path: str) -> List[Dict]:
        """
        PDF 扫描件视觉解析
        
        将 PDF 每页转为图片，通过 OCR 提取文字，
        同时将图片转为 base64 走 Qwen3-VL 原生视觉路径。
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            分片列表 [{"image": "base64...", "ocr_ref": "..."}]
        """
        chunks = []
        images = convert_from_path(file_path, dpi=120)
        
        for idx, img in enumerate(images):
            # 1. OCR 提取文字作为元数据参考
            ocr_ref = ""
            if OCR_ENGINE:
                result, _ = OCR_ENGINE(np.array(img))
                if result:
                    ocr_ref = " ".join([line[1] for line in result])
            
            # 2. 图片转 base64 走视觉向量通路
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="JPEG")
            b64_img = base64.b64encode(buf.getvalue()).decode()
            
            chunks.append({
                "image": b64_img,
                "ocr_ref": ocr_ref[:300]  # 保留前300字符作为参考
            })
            logger.info(f"   🔍 第 {idx + 1}/{len(images)} 页已视觉解析")
        
        return chunks
    
    # =========================================================================
    # 状态管理
    # =========================================================================
    
    def _ensure_state_dirs(self, base_dir: str):
        """
        确保状态目录存在
        
        Args:
            base_dir: 项目根目录
        """
        for state in [STATE_INCOMING, STATE_PROCESSED, STATE_FAILED]:
            os.makedirs(os.path.join(base_dir, state), exist_ok=True)
    
    def _get_processed_files(self) -> Set[str]:
        """获取已入库文件记录（断点续传）"""
        if os.path.exists(self.progress_log):
            with open(self.progress_log, 'r') as f:
                return set(json.load(f))
        return set()
    
    def _mark_processed(self, filename: str):
        """标记文件已处理"""
        processed = self._get_processed_files()
        processed.add(filename)
        with open(self.progress_log, 'w') as f:
            json.dump(list(processed), f)
    
    # =========================================================================
    # 主流程
    # =========================================================================
    
    def ingest(
        self,
        project_dir: str,
        project_tag: str,
        watch_mode: bool = False,
        poll_interval: int = 30
    ):
        """
        执行入库主流程
        
        Args:
            project_dir: 项目根目录（包含 incoming/processed/failed 子目录）
            project_tag: 项目标签（用于数据隔离）
            watch_mode: 是否开启监控模式
            poll_interval: 监控轮询间隔（秒）
        """
        # 参数校验
        if not project_tag:
            logger.error("❌ project_tag 不能为空")
            return
        
        # 确保状态目录存在
        self._ensure_state_dirs(project_dir)
        
        # 获取 incoming 目录路径
        incoming_dir = os.path.join(project_dir, STATE_INCOMING)
        
        if not os.path.isdir(incoming_dir):
            logger.error(f"❌ incoming 目录不存在: {incoming_dir}")
            return
        
        logger.info(f"\n{'=' * 60}")
        logger.info(f"📥 Sovereign-IQ 项目底稿入库系统")
        logger.info(f"{'=' * 60}")
        logger.info(f"   项目标签: {project_tag}")
        logger.info(f"   目标库:   {SHARED_COLLECTION}")
        logger.info(f"   监控模式: {'开启' if watch_mode else '关闭'}")
        logger.info(f"{'=' * 60}\n")
        
        # ----------------------------------------------------------------
        # 单次处理循环
        # ----------------------------------------------------------------
        def process_once():
            # 获取待处理文件
            all_files = [
                f for f in os.listdir(incoming_dir)
                if os.path.isfile(os.path.join(incoming_dir, f))
                and f.lower().endswith(('.pdf', '.docx', '.md', '.txt'))
            ]
            
            # 断点续传：跳过已处理文件
            processed_history = self._get_processed_files()
            pending_files = [f for f in all_files if f not in processed_history]
            
            if not pending_files:
                logger.info("📭 暂无新文件需要处理")
                return
            
            logger.info(f"📂 待处理文件: {len(pending_files)} 个")
            logger.info(f"   文件列表: {', '.join(pending_files)}")
            
            # 逐文件处理
            for fname in pending_files:
                fpath = os.path.join(incoming_dir, fname)
                logger.info(f"\n🔄 正在处理: {fname}")
                
                # 1. 解析文件
                chunks = self._parse_file(fpath)
                
                if not chunks:
                    logger.warning(f"   ⚠️ 解析结果为空，移动至 failed")
                    shutil.move(fpath, os.path.join(project_dir, STATE_FAILED, fname))
                    continue
                
                logger.info(f"   📦 解析完成，共 {len(chunks)} 个分片")
                
                # 2. 分批向量化并入库
                success = True
                total_inserted = 0
                
                for i in range(0, len(chunks), self.batch_size):
                    batch = chunks[i:i + self.batch_size]
                    vectors = self._get_embeddings(batch)
                    
                    if len(vectors) != len(batch):
                        logger.error(f"   ❌ 向量化失败，终止入库")
                        success = False
                        break
                    
                    # 组装元数据
                    meta_list = []
                    for item in batch:
                        meta = {
                            "file_name": fname,
                            "project_tag": project_tag,
                            "source": "human",          # 标记来源：人类
                            "type": "fact",            # 标记类型：事实
                            "round": 0,                # 底稿轮次为0
                            "ingest_time": datetime.now().isoformat(),
                            "content_preview": item.get("text", "")[:200] if "text" in item else f"[Vision] OCR: {item.get('ocr_ref', '')[:100]}"
                        }
                        meta_list.append(meta)
                    
                    # 写入 Milvus
                    try:
                        # 注意：字段顺序需与 Collection Schema 一致
                        # Schema: id, vector, project_tag, metadata
                        self.collection.insert([
                            vectors,                           # vector
                            [project_tag] * len(vectors),     # project_tag
                            [json.dumps(m, ensure_ascii=False) for m in meta_list]  # metadata
                        ])
                        total_inserted += len(vectors)
                    except Exception as e:
                        logger.error(f"   ❌ Milvus 写入失败: {e}")
                        success = False
                        break
                
                # 3. 文件状态闭环
                if success:
                    shutil.move(fpath, os.path.join(project_dir, STATE_PROCESSED, fname))
                    self._mark_processed(fname)
                    logger.info(f"   ✅ 入库完成，移动至 processed")
                else:
                    shutil.move(fpath, os.path.join(project_dir, STATE_FAILED, fname))
                    logger.info(f"   ❌ 入库失败，移动至 failed")
                
                logger.info(f"   📊 本次入库向量数: {total_inserted}")
            
            # 刷新 Milvus 缓冲
            self.collection.flush()
            
            # 显示当前库状态
            logger.info(f"\n📈 共享库当前状态:")
            logger.info(f"   集合名称: {SHARED_COLLECTION}")
            logger.info(f"   总实体数: {self.collection.num_entities}")
        
        # ----------------------------------------------------------------
        # 执行或循环
        # ----------------------------------------------------------------
        if watch_mode:
            logger.info(f"\n🔄 开启监控模式，每 {poll_interval} 秒轮询一次 (Ctrl+C 退出)")
            try:
                while True:
                    process_once()
                    logger.info(f"\n☕ 监控中... (Ctrl+C 退出)")
                    time.sleep(poll_interval)
            except KeyboardInterrupt:
                logger.info("\n\n👋 监控已停止")
        else:
            process_once()
        
        # 关闭连接
        connections.disconnect("default")
        logger.info("\n✅ 入库流程结束")


# ============================================================================
# 交互入口
# ============================================================================

def main():
    """人类交互式入口"""
    
    print("\n" + "=" * 60)
    print("📥 Sovereign-IQ | 项目底稿入库控制台 v1.0")
    print("=" * 60)
    print("\n💡 使用说明:")
    print("   1. 将待入库底稿放入项目的 incoming 目录")
    print("   2. 支持格式: PDF, DOCX, MD, TXT")
    print("   3. 运行本脚本，按提示输入项目标签")
    print()
    
    # 输入项目根目录
    project_dir = input("📁 请输入项目根目录绝对路径: ").strip()
    
    if not os.path.isdir(project_dir):
        print(f"❌ 目录不存在: {project_dir}")
        sys.exit(1)
    
    # 输入项目标签
    project_tag = input("🏷️ 请输入项目标签 (如 YUSHU_2026): ").strip()
    
    if not project_tag:
        print("❌ project_tag 不能为空")
        sys.exit(1)
    
    # 询问监控模式
    watch_input = input("🔄 是否开启监控模式? (y/N): ").strip().lower()
    watch_mode = watch_input == 'y'
    
    # 解析监控间隔
    poll_interval = 30
    if watch_mode:
        poll_input = input("⏱️  轮询间隔秒数 (默认30): ").strip()
        if poll_input.isdigit():
            poll_interval = int(poll_input)
    
    print("\n" + "-" * 60)
    
    # 执行入库
    ingestor = ProjectIngestor()
    ingestor.ingest(
        project_dir=project_dir,
        project_tag=project_tag,
        watch_mode=watch_mode,
        poll_interval=poll_interval
    )


if __name__ == "__main__":
    main()
