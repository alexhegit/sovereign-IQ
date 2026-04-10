#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import asyncio
import base64
import logging
import aiohttp
import time
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Set, Tuple, Optional
from pathlib import Path

# 核心格式解析库
import fitz  # PyMuPDF
from docx import Document  # python-docx
from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm

# ==================== 核心配置 ====================
DASHSCOPE_API_KEY = ""
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MODEL_NAME = "qwen3-vl-embedding"
VECTOR_DIM = 1024
API_ENDPOINT = ""

# 极速入库参数
CONCURRENT_REQUESTS = 8  # API 并发控制
CHUNK_SIZE = 800         # 文本分块长度
CHUNK_OVERLAP = 150      # 分块重叠
TIMEOUT_API = 45         # API 超时设置

console = Console()
logging.basicConfig(level=logging.ERROR)

class AsyncKnowledgeIngestor:
    ROLE_REGISTRY = {
        "1": {"name": "ic_chairman_ws", "desc": "投委会主席"},
        "2": {"name": "ic_finance_auditor_ws", "desc": "财务审计官"},
        "3": {"name": "ic_sector_expert_ws", "desc": "行业专家"},
        "4": {"name": "ic_legal_scanner_ws", "desc": "法务专家 "},
        "5": {"name": "ic_strategist_ws", "desc": "战略专家"},
        "6": {"name": "ic_risk_controller_ws", "desc": "风险官"},
        "7": {"name": "ic_master_coordinator_ws", "desc": "投委会秘书"},
        "8": {"name": "ic_collaboration_shared_ws", "desc": "协同共享工作区"},
        "9": {"name": "ic_archive_sop_ws", "desc": "机构历史案例库 (SOP资产)"}
    }

    def __init__(self, collection_id: str, reset: bool = False):
        role_info = self.ROLE_REGISTRY.get(collection_id)
        self.collection_name = role_info["name"]
        self.role_desc = role_info["desc"]
        self.progress_file = f".progress_{self.collection_name}.json"
        self._init_milvus(reset)
        
    def _init_milvus(self, reset: bool):
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        if reset and utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            if os.path.exists(self.progress_file): os.remove(self.progress_file)
        
        if not utility.has_collection(self.collection_name):
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
                FieldSchema(name="batch_tag", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            col = Collection(self.collection_name, CollectionSchema(fields))
            col.create_index("vector", {"metric_type": "IP", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 128}})
        
        self.collection = Collection(self.collection_name)
        self.collection.load()

    async def _fetch_embedding(self, session: aiohttp.ClientSession, item: Dict, semaphore: asyncio.Semaphore) -> Optional[List[float]]:
        headers = {"Authorization": f"Bearer {DASHSCOPE_API_KEY}", "Content-Type": "application/json"}
        content = {"text": item["content"]} if item["type"] == "text" else {"text": "visual content", "image": item["image"]}
        payload = {"model": MODEL_NAME, "input": {"contents": [content]}, "parameters": {"dimension": VECTOR_DIM}}

        async with semaphore:
            for attempt in range(3):
                try:
                    async with session.post(API_ENDPOINT, headers=headers, json=payload, timeout=TIMEOUT_API) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            vec = data["output"]["embeddings"][0]["embedding"]
                            arr = np.array(vec)
                            return (arr / (np.linalg.norm(arr) + 1e-12)).tolist()
                        elif resp.status == 429:
                            await asyncio.sleep(2 ** attempt)
                        else:
                            await asyncio.sleep(1)
                except Exception:
                    await asyncio.sleep(1)
            return None

    def _split_text(self, text: str, fname: str, meta_extra: Dict = None) -> List[Dict]:
        """统一的文本切块逻辑"""
        items = []
        clean_text = " ".join(text.split())
        for i in range(0, len(clean_text), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk = clean_text[i : i + CHUNK_SIZE]
            meta = {"source": fname, "type": "text_chunk"}
            if meta_extra: meta.update(meta_extra)
            items.append({"type": "text", "content": chunk, "meta": meta})
        return items

    def _parse_pdf(self, path: str) -> List[Dict]:
        items = []
        doc = fitz.open(path)
        fname = os.path.basename(path)
        for page_idx, page in enumerate(doc):
            text = page.get_text("text").strip()
            # 文本提取
            if len(text) > 10:
                items.extend(self._split_text(text, fname, {"page": page_idx + 1}))
            # 视觉提取（针对扫描件/图表页）
            if len(text) < 100:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
                img_b64 = base64.b64encode(pix.tobytes("jpg")).decode()
                items.append({
                    "type": "image", 
                    "image": f"data:image/jpeg;base64,{img_b64}",
                    "meta": {"page": page_idx + 1, "source": fname, "is_visual": True}
                })
        doc.close()
        return items

    def _parse_docx(self, path: str) -> List[Dict]:
        doc = Document(path)
        full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return self._split_text(full_text, os.path.basename(path), {"format": "docx"})

    def _parse_plain_text(self, path: str) -> List[Dict]:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self._split_text(content, os.path.basename(path), {"format": Path(path).suffix[1:]})

    async def process_file(self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, file_path: str, batch_tag: str) -> int:
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            items = self._parse_pdf(file_path)
        elif ext == '.docx':
            items = self._parse_docx(file_path)
        elif ext in ['.md', '.txt']:
            items = self._parse_plain_text(file_path)
        else:
            return 0

        if not items: return 0
        tasks = [self._fetch_embedding(session, it, semaphore) for it in items]
        results = await asyncio.gather(*tasks)
        
        vectors, metas = [], []
        for i, vec in enumerate(results):
            if vec:
                vectors.append(vec)
                metas.append(items[i]["meta"])
        
        if vectors:
            self.collection.insert([vectors, [batch_tag] * len(vectors), metas])
            return len(vectors)
        return 0

    async def run(self, data_path: str, batch_tag: str):
        # 扫描所有支持的格式
        extensions = ['*.pdf', '*.docx', '*.md', '*.txt']
        files = []
        for ext in extensions:
            files.extend(list(Path(data_path).glob(f"**/{ext}")))
        
        files = sorted([str(f) for f in files])
        processed = self._load_progress()
        pending = [f for f in files if os.path.basename(f) not in processed]
        
        if not pending:
            console.print("[yellow]当前目录无新文档需处理。[/yellow]")
            return

        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        async with aiohttp.ClientSession() as session:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TimeElapsedColumn(), console=console) as progress:
                overall_task = progress.add_task(f"[cyan]🚀 全格式注入: {self.collection_name}", total=len(pending))
                for f_path in pending:
                    fname = os.path.basename(f_path)
                    inserted = await self.process_file(session, semaphore, f_path, batch_tag)
                    if inserted > 0:
                        processed.add(fname)
                        self._save_progress(processed)
                        progress.update(overall_task, advance=1, description=f"✅ {fname[:15]} ({inserted}条)")
                    else:
                        progress.update(overall_task, advance=1, description=f"❌ 跳过: {fname[:15]}")
        self.collection.flush()
        console.print(f"\n[bold green]🎉 入库任务结束。总实体数: {self.collection.num_entities}[/bold green]")

    def _load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f: return set(json.load(f))
        return set()

    def _save_progress(self, processed):
        with open(self.progress_file, 'w') as f: json.dump(list(processed), f)

# --- 交互式主入口 ---
def main():
    table = Table(title="[bold magenta]SIQ 投委会全格式知识库入库系统 V4.0[/bold magenta]", show_lines=True)
    table.add_column("ID", style="cyan", justify="center")
    table.add_column("工作区 (Collection)", style="green")
    table.add_column("专家描述", style="white")

    for k, v in AsyncKnowledgeIngestor.ROLE_REGISTRY.items():
        table.add_row(k, v["name"], v["desc"])
    
    console.print("\n", table)

    try:
        choice = Prompt.ask("\n[bold yellow]选择目标空间 ID[/bold yellow]", choices=[str(i) for i in range(1, 10)], default="请输入")
        default_dir = "/home/xsuper/Downloads/knowledge/strategist"
        data_dir = Prompt.ask(f"[bold yellow]输入文档目录路径[/bold yellow]", default=default_dir)
        
        if not os.path.exists(data_dir):
            console.print(f"[bold red]路径不存在: {data_dir}[/bold red]")
            return

        tag = Prompt.ask("[bold yellow]输入批次标签[/bold yellow]", default=f"ingest_{datetime.now().strftime('%m%d')}")
        reset = Confirm.ask("[bold red]是否重置该空间？[/bold red]", default=False)

        engine = AsyncKnowledgeIngestor(choice, reset=reset)
        console.print(f"\n[bold green]🚀 引擎启动: {engine.role_desc}[/bold green]\n")
        asyncio.run(engine.run(data_dir, tag))

    except KeyboardInterrupt:
        console.print("\n[bold red]已手动停止。[/bold red]")

if __name__ == "__main__":
    main()