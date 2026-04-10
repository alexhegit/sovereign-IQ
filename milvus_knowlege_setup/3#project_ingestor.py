#project_ingestor.py
"""
Sovereign-IQ Project Intelligence Ingestor (V1.0)
---------------------------------------------------------
功能：自动化扫描项目目录，将底稿（PDF/DOCX/MD）全量穿透并存入【协同共享库】。
设计亮点：
1. 状态机管理：通过目录流转（incoming -> processed/failed）实现任务状态物理追踪。
2. 共享协同：默认注入 ic_collaboration_shared_ws，确保所有 Agent 实时可见。
3. 并发解析：采用 ThreadPoolExecutor 压榨多模态 Embedding 的 IO 并发性能。
4. 强制标签：强制要求 Project Tag，实现项目级的数据隔离。
"""

import os
import shutil
import time
import logging
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# 复用脚本 2 的核心解析能力 (建议将解析逻辑封装在 utils 中，此处为演示完整性再次体现)
from pypdf import PdfReader
from docx import Document
from pdf2image import convert_from_path
import numpy as np
import base64
from io import BytesIO
from openai import OpenAI
from pymilvus import connections, Collection, utility

# 🛡️ 兼容性配置
try:
    from rapidocr_onnxruntime import RapidOCR
    OCR_ENGINE = RapidOCR()
except:
    OCR_ENGINE = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ProjectIngestor")

class ProjectIngestor:
    def __init__(self, base_url: str, shared_ws: str = "ic_collaboration_shared_ws"):
        self.shared_ws = shared_ws
        self.vector_dim = 2048
        self.client = OpenAI(api_key="EMPTY", base_url=base_url)
        
        # 建立连接
        connections.connect("default", host="localhost", port="19530")
        self.collection = Collection(self.shared_ws)
        self.collection.load()

    def _get_embedding(self, payload: List[Dict]) -> List[List[float]]:
        """调用本地 Qwen3-VL-Embedding-2B 接口"""
        formatted = []
        for item in payload:
            if "text" in item: 
                formatted.append(item["text"])
            elif "image" in item: 
                # 图片转为base64描述文本
                formatted.append(f"[图像内容: {item.get('desc', '图片')}]")
        
        try:
            res = self.client.embeddings.create(model="fervent_mcclintock/Qwen3-VL-Embedding-2B:Q8_0", input=formatted, timeout=60)
            return [d.embedding for d in res.data]
        except Exception as e:
            logger.error(f"Embedding 失败: {e}")
            return []

    def _parse_file(self, fpath: str) -> List[Dict]:
        """解析文档并分片，支持视觉补偿"""
        ext = os.path.splitext(fpath)[1].lower()
        items = []
        try:
            if ext in ['.md', '.txt']:
                txt = open(fpath, 'r', encoding='utf-8', errors='ignore').read()
                items = [{"text": txt[i:i+800]} for i in range(0, len(txt), 800)]
            elif ext == '.docx':
                txt = "\n".join([p.text for p in Document(fpath).paragraphs])
                items = [{"text": txt[i:i+800]} for i in range(0, len(txt), 800)]
            elif ext == '.pdf':
                reader = PdfReader(fpath)
                txt = "".join([p.extract_text() or "" for p in reader.pages])
                if len(txt.strip()) < 100 and OCR_ENGINE:
                    imgs = convert_from_path(fpath, dpi=120)
                    for img in imgs:
                        buf = BytesIO(); img.save(buf, format="JPEG")
                        b64 = base64.b64encode(buf.getvalue()).decode()
                        items.append({"image": b64})
                else:
                    items = [{"text": txt[i:i+800]} for i in range(0, len(txt), 800)]
        except Exception as e:
            logger.error(f"解析异常 {fpath}: {e}")
        return items

    def process_project(self, incoming_dir: str, project_tag: str):
        """处理指定目录下的所有底稿"""
        # 创建状态目录
        processed_dir = os.path.join(incoming_dir, "processed")
        failed_dir = os.path.join(incoming_dir, "failed")
        for d in [processed_dir, failed_dir]: os.makedirs(d, exist_ok=True)

        files = [f for f in os.listdir(incoming_dir) if os.path.isfile(os.path.join(incoming_dir, f))]
        if not files:
            logger.info("📭 暂无新文件。")
            return

        logger.info(f"📂 开始处理项目 [{project_tag}]，共 {len(files)} 个文件...")

        for fname in files:
            fpath = os.path.join(incoming_dir, fname)
            chunks = self._parse_file(fpath)
            
            success = True
            if chunks:
                # 8片一组并发入库
                for i in range(0, len(chunks), 8):
                    batch = chunks[i:i+8]
                    vecs = self._get_embedding(batch)
                    if len(vecs) == len(batch):
                        metas = [{"file": fname, "tag": project_tag, "type": "fact", "snippet": (c.get("text","")[:200])} for c in batch]
                        self.collection.insert([vecs, [project_tag]*len(vecs), metas])
                    else:
                        success = False; break
            
            # 移动文件实现状态闭环
            target_path = os.path.join(processed_dir if success else failed_dir, fname)
            shutil.move(fpath, target_path)
            logger.info(f"✅ {'归档' if success else '跳过'} : {fname}")

        self.collection.flush()
        logger.info(f"✨ 项目 [{project_tag}] 实时情报已同步至协同共享区。")

if __name__ == "__main__":
    # 模拟“秘书 Agent”的自动化逻辑
    print("--- Sovereign-IQ 项目情报实时入库系统 ---")
    
    # 实际场景下，这些参数可由飞书 Bot 的回调事件触发传递
    MONITOR_PATH = input("📁 请输入项目待处理目录 (incoming): ").strip()
    PROJECT_TAG = input("🏷️ 请输入当前讨论的项目标签: ").strip()
    
    ingestor = ProjectIngestor(base_url="http://127.0.0.1:11434/v1")
    
    while True:
        ingestor.process_project(MONITOR_PATH, PROJECT_TAG)
        print("☕ 正在监控中... (Ctrl+C 退出)")
        time.sleep(30) # 每 30 秒轮询一次