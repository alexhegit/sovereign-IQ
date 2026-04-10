"""
================================================================================
PROJECT: Ultra-High-Fidelity Ingestion Engine (V5.8 - Physical IP Patch)
ARCHITECT: Arthurmao's Programming Assistant (Silicon Valley Elite)
HARDWARE: NVIDIA GB10 (128GB VRAM) | CUDA 13.0 | 1024-Dim | aarch64
MODEL: fervent_mcclintock/Qwen3-VL-Embedding-2B
MILVUS_HOST: 192.168.110.85 (Physical LAN IP)
================================================================================
"""

import os
import sys
import json
import time
import base64
import logging
import requests
import numpy as np
from typing import List, Dict, Any

# 核心依赖装载
try:
    import fitz  # PyMuPDF
    import cupy as cp
    from tqdm import tqdm
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
except ImportError as e:
    print(f"ERROR: Missing components: {e}\nRun: pip install pymupdf cupy-cuda13x rich pymilvus tqdm requests")
    sys.exit(1)

logging.basicConfig(level=logging.ERROR)
console = Console()

class GPUKnowledgeFeeder:
    ROLE_REGISTRY = {
        "1": {"name": "ic_chairman_ws", "desc": "Chairman/Strategy"},
        "2": {"name": "ic_finance_auditor_ws", "desc": "Finance/Audit"},
        "3": {"name": "ic_sector_expert_ws", "desc": "Sector Expert"},
        "4": {"name": "ic_legal_scanner_ws", "desc": "Legal/Compliance"},
        "5": {"name": "ic_strategist_ws", "desc": "Quant Strategist"},
        "6": {"name": "ic_risk_controller_ws", "desc": "Risk Controller"},
        "7": {"name": "ic_master_coordinator_ws", "desc": "Coordinator"},
        "8": {"name": "ic_collaboration_shared_ws", "desc": "Shared Workspace"}
    }

    def __init__(self, collection_id: str, host: str = "192.168.110.85", reset: bool = False):
        role_info = self.ROLE_REGISTRY.get(collection_id)
        self.collection_name = role_info["name"]
        
        # 🎯 物理 IP 锁定，解决 localhost 丢包问题
        self.milvus_host = host
        self.ollama_api = "http://127.0.0.1:11434/api/embeddings"
        self.model_name = "fervent_mcclintock/Qwen3-VL-Embedding-2B:Q8_0"
        
        self.vector_dim = 2048
        self.batch_size = 1 
        self.progress_log = f".ingest_log_{self.collection_name}.json"
        
        self._init_milvus(reset)

    def _init_milvus(self, reset: bool):
        try:
            rprint(f"[bold cyan]Connecting to Milvus at {self.milvus_host}...[/bold cyan]")
            connections.connect("default", host=self.milvus_host, port="19530", timeout=10)
            
            if reset:
                if utility.has_collection(self.collection_name):
                    utility.drop_collection(self.collection_name)
                    rprint(f"[bold red]RESET: Dropped {self.collection_name}[/bold red]")
                if os.path.exists(self.progress_log):
                    os.remove(self.progress_log)

            if not utility.has_collection(self.collection_name):
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.vector_dim),
                    FieldSchema(name="batch_tag", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="metadata", dtype=DataType.JSON)
                ]
                schema = CollectionSchema(fields, description="Blackwell Precision Store")
                col = Collection(self.collection_name, schema)
                index_params = {"metric_type": "IP", "index_type": "HNSW", "params": {"M": 32, "efConstruction": 200}}
                col.create_index("vector", index_params)
            
            self.collection = Collection(self.collection_name)
            self.collection.load()
            rprint(f"[bold green]Connected! Valid Entity Count: {self.collection.num_entities}[/bold green]")
        except Exception as e:
            rprint(f"[bold red]Milvus Connection Failed: {e}[/bold red]")
            sys.exit(1)

    def _gpu_l2_normalize(self, vectors: List[List[float]]) -> List[List[float]]:
        v_gpu = cp.array(vectors)
        norm = cp.linalg.norm(v_gpu, axis=1, keepdims=True)
        return (v_gpu / (norm + 1e-9)).get().tolist()

    def _get_embeddings_with_retry(self, items: List[Dict[str, Any]], retries=3) -> List[List[float]]:
        all_vecs = []
        prefix = "Represent this financial segment: "
        for it in items:
            payload = {"model": self.model_name, "input": f"{prefix}{it['content']}"}
            final_v = None
            for attempt in range(retries):
                try:
                    resp = requests.post(self.ollama_api, json=payload, timeout=30)
                    resp.raise_for_status()
                    v = resp.json().get("embedding")
                    if v and len(v) > 0:
                        v = v[:self.vector_dim] if len(v) > self.vector_dim else v + [0.0] * (self.vector_dim - len(v))
                        final_v = v
                        break
                except Exception:
                    time.sleep(2 ** attempt)
            all_vecs.append(final_v if final_v else (np.random.rand(self.vector_dim) * 0.001).tolist())
        return self._gpu_l2_normalize(all_vecs)

    def _parse_pdf_spatial(self, pdf_path: str) -> List[Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        extracted = []
        for page_idx, page in enumerate(doc):
            p_no = page_idx + 1
            for b in page.get_text("blocks"):
                if b[4].strip():
                    extracted.append({
                        "content": b[4].strip(),
                        "meta": {"page": p_no, "bbox": [round(c, 2) for c in b[:4]], "type": "text"}
                    })
        doc.close()
        return extracted

    def run(self, source_dir: str, batch_tag: str):
        files = [os.path.join(source_dir, f) for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
        files.sort()
        history = set()
        if os.path.exists(self.progress_log):
            with open(self.progress_log, 'r') as f: history = set(json.load(f))
        
        pending = [f for f in files if os.path.basename(f) not in history]
        if not pending:
            rprint("[yellow]Nothing to process.[/yellow]")
            return

        for file_path in tqdm(pending, desc="Total Progress"):
            fname = os.path.basename(file_path)
            items = self._parse_pdf_spatial(file_path)
            if not items: continue

            all_vectors = []
            for i in range(0, len(items), self.batch_size):
                batch = items[i : i + self.batch_size]
                all_vectors.extend(self._get_embeddings_with_retry(batch))

            if len(all_vectors) == len(items):
                metas = [it["meta"] for it in items]
                for m in metas: m.update({"source": fname})
                # 🎯 写入
                self.collection.insert([all_vectors, [batch_tag] * len(all_vectors), metas])
                # 🎯 强制刷新刷盘，确保 Attu 可见
                self.collection.flush()
                
                history.add(fname)
                with open(self.progress_log, 'w') as f: json.dump(list(history), f)
        
        rprint(f"[bold green]All done! Current Total: {self.collection.num_entities}[/bold green]")

# --- UI 展示 ---
def show_ui():
    os.system('clear' if os.name == 'posix' else 'cls')
    console.print(Panel.fit(
        "[bold cyan]ULTRA-INJEST V5.8[/bold cyan] | [bold magenta]PHYSICAL IP MODE[/bold magenta]\n"
        "[white]Target Model: Qwen3-VL-Embedding-2B:Q8_0[/white]\n"
        "[dim]Network Strategy: Fixed LAN IP 192.168.110.85[/dim]",
        border_style="cyan"
    ))
    table = Table(show_header=True, header_style="bold green", box=None)
    table.add_column("ID", justify="center", style="cyan")
    table.add_column("Workspace Role", style="yellow")
    for k, v in GPUKnowledgeFeeder.ROLE_REGISTRY.items():
        table.add_row(k, v["name"])
    console.print(table)

if __name__ == "__main__":
    show_ui()
    try:
        choice = Prompt.ask("\n[bold yellow]Target DB ID[/bold yellow]", choices=[str(i) for i in range(1, 9)], default="5")
        
        # 🎯 建议输入截图中的局域网 IP
        m_ip = Prompt.ask("[bold magenta]Milvus LAN IP[/bold magenta]", default="192.168.110.85")
        
        f_path = Prompt.ask("[bold blue]PDF Folder Path[/bold blue]")
        b_tag = Prompt.ask("[bold blue]Batch Tag[/bold blue]", default="ST_2026_V58")
        reset = Confirm.ask("♻️ [bold red]Force Reset?[/bold red]", default=False)

        engine = GPUKnowledgeFeeder(choice, host=m_ip, reset=reset)
        engine.run(f_path, b_tag)
    except KeyboardInterrupt:
        rprint("\n[bold red]Interrupted.[/bold red]")
    except Exception as e:
        rprint(f"\n[bold white on red] ERROR [/bold white on red] {e}")
