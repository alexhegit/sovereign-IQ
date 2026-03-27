import os
import json
import time
import requests
import numpy as np
from typing import List, Set
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 解析与 OCR 库
from pypdf import PdfReader
from docx import Document
from pptx import Presentation
from pdf2image import convert_from_path
from paddleocr import PaddleOCR

# Milvus
from pymilvus import (
    connections, Collection, FieldSchema,
    CollectionSchema, DataType, utility
)
from tqdm import tqdm

<<<<<<< Updated upstream
# 🛡️ 环境加固
os.environ["OBJC_DISABLE_INITIALIZE_FOR_SAFETY"] = "YES"


class UniversalLegalIngestor:
    def __init__(self, config: dict):
        self.cfg = config
        self.char_limit = 800
=======
# 🛡️ 解决 macOS 下 gRPC 与多进程冲突及网络警告
os.environ["OBJC_DISABLE_INITIALIZE_FOR_SAFETY"] = "YES"


class UltimateLegalIngestor:
    def __init__(self, collection_name: str, group_id: str, api_key: str, progress_file: str):
        self.collection_name = collection_name
        self.group_id = group_id
        self.api_key = api_key
        self.char_limit = 800  # 物理切分上限
>>>>>>> Stashed changes
        self.vector_dim = 1536
        self._ocr = None

<<<<<<< Updated upstream
        # 1. 网络连接优化
        self.session = self._create_session()

        # 2. 连接 Milvus（增量模式）
=======
        # 1. 建立具备自动重试能力的 Session
        self.session = self._create_session()

        # 2. 连接 Milvus
>>>>>>> Stashed changes
        connections.connect("default", host="localhost", port="19530")
        self.collection = self._ensure_collection_exists()
        self.collection.load()

        # 3. 接口配置
        self.api_url = f"https://api.minimax.chat/v1/embeddings?GroupId={self.cfg['GROUP_ID']}"
        self.headers = {"Authorization": f"Bearer {self.cfg['API_KEY']}", "Content-Type": "application/json"}

    def _create_session(self):
        session = requests.Session()
<<<<<<< Updated upstream
        retries = Retry(total=5, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session
=======
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    @property
    def ocr(self):
        if self._ocr is None:
            print("⏳ 正在加载 PaddleOCR 模型...")
            self._ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        return self._ocr
>>>>>>> Stashed changes

    def _ensure_collection_exists(self) -> Collection:
        if utility.has_collection(self.cfg['COLLECTION']):
            return Collection(self.cfg['COLLECTION'])

        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.vector_dim)
        ]
        schema = CollectionSchema(fields, "通用法律法规语义库")
        col = Collection(self.cfg['COLLECTION'], schema)
        col.create_index("vector", {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
        return col

    @property
    def ocr(self):
        if self._ocr is None:
            self._ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        return self._ocr

    def _extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif ext == '.docx':
                text = "\n".join([p.text for p in Document(file_path).paragraphs])
            elif ext == '.pdf':
                reader = PdfReader(file_path)
                text = "\n".join([p.extract_text() or "" for p in reader.pages])
                if len(text.strip()) < 50:
                    images = convert_from_path(file_path, dpi=150)
                    text = "\n".join(
<<<<<<< Updated upstream
                        [" ".join([l[1][0] for l in self.ocr.ocr(np.array(i), cls=True)[0]]) for i in images if
                         self.ocr.ocr(np.array(i), cls=True)[0]])
        except Exception:
            pass
        return text

    def get_embeddings(self, texts: List[str]):
        try:
            res = self.session.post(self.api_url, headers=self.headers,
                                    json={"model": "embo-01", "texts": texts, "type": "db"}, timeout=45)
            if res.status_code == 200: return res.json().get("vectors", [])
        except Exception:
            pass
        return None
=======
                        [" ".join([l[1][0] for l in self.ocr.ocr(np.array(i), cls=True)[0]]) for i in images])
        except Exception as e:
            print(f"⚠️ 解析失败 {file_path}: {e}")
        return text

    def _robust_split(self, text: str) -> List[str]:
        text = text.replace('\0', '').strip()
        if not text: return []
        # 物理硬切分
        return [text[i: i + self.char_limit] for i in range(0, len(text), self.char_limit)]
>>>>>>> Stashed changes

    def get_embeddings(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        for i in range(max_retries):
            try:
                res = self.session.post(self.api_url, headers=self.headers,
                                        json={"model": "embo-01", "texts": texts, "type": "db"}, timeout=30)
                if res.status_code == 200:
                    return res.json().get("vectors", [])
                elif res.status_code == 429:
                    time.sleep((i + 1) * 2)
            except Exception as e:
                print(f"⚠️ 网络波动 (第 {i + 1} 次重试): {e}")
                time.sleep(2)
        return []

    def _load_progress(self) -> Set[str]:
        if os.path.exists(self.cfg['PROGRESS_FILE']):
            with open(self.cfg['PROGRESS_FILE'], 'r', encoding='utf-8') as f:
                try:
                    return set(json.load(f))
                except:
                    return set()
        return set()

    def _save_progress(self, file_name: str):
<<<<<<< Updated upstream
        processed = list(self._load_progress())
        processed.append(file_name)
        with open(self.cfg['PROGRESS_FILE'], 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False)

    def run(self):
        path = self.cfg['DATA_PATH']
        all_files = sorted([f for f in os.listdir(path) if f.lower().endswith(('.pdf', '.docx', '.md', '.txt'))])
        processed = self._load_progress()
        pending = [f for f in all_files if f not in processed]

        tqdm.write(f"📊 任务启动: 总计 {len(all_files)} | 已完成 {len(processed)} | 待处理 {len(pending)}")

        for file_name in tqdm(pending, desc="📁 总进度"):
            content = self._extract_text(os.path.join(path, file_name))
            if not content.strip():
                self._save_progress(file_name);
                continue

            # 物理切片
            chunks = [content[i: i + self.char_limit] for i in range(0, len(content), self.char_limit)]
            total_batches = (len(chunks) + 9) // 10
            tqdm.write(f"📄 处理中: {file_name} (共 {len(chunks)} 片 / {total_batches} 批次)")
=======
        processed = self._load_progress()
        processed.add(file_name)
        with open(self.progress_file, 'w') as f: json.dump(list(processed), f)

    def process_directory(self, dir_path: str):
        if not os.path.exists(dir_path):
            print(f"❌ 错误：路径不存在 -> {dir_path}");
            return

        all_files = sorted([f for f in os.listdir(dir_path) if
                            os.path.splitext(f)[1].lower() in {'.pdf', '.docx', '.pptx', '.txt', '.md'}])
        processed = self._load_progress()
        pending = [f for f in all_files if f not in processed]

        print(f"📂 发现 {len(all_files)} 个文件，准备处理 {len(pending)} 个新任务...")

        for file_name in tqdm(pending, desc="总进度"):
            file_path = os.path.join(dir_path, file_name)
            content = self._extract_text(file_path)

            # --- 重新加入的切片显示逻辑 ---
            chunks = self._robust_split(content)
            print(f"\n📝 文件 '{file_name}' -> 被切分为 {len(chunks)} 个片段")

            all_chunks_success = True
>>>>>>> Stashed changes

            file_success = True
            for i in range(0, len(chunks), 10):
<<<<<<< Updated upstream
                batch_idx = i // 10 + 1
                batch = chunks[i: i + 10]

                vectors = self.get_embeddings(batch)
                if vectors and len(vectors) == len(batch):
                    try:
                        self.collection.insert([
                            [file_name] * len(vectors),
                            [t[:3900] for t in batch],
                            vectors
                        ])
                        tqdm.write(f"  └─ ✅ 批次 {batch_idx}/{total_batches} 成功入库")
                    except Exception as e:
                        tqdm.write(f"  └─ ❌ Milvus 报错: {e}")
                        file_success = False;
                        break
                else:
                    tqdm.write(f"  └─ ❌ API 失败 (批次 {batch_idx})")
                    file_success = False;
                    break
                time.sleep(0.4)

            if file_success:
                self._save_progress(file_name)
                tqdm.write(f"🏁 文件 '{file_name}' 全部入库成功！")
            else:
                tqdm.write(f"⚠️ 文件 '{file_name}' 处理中途受阻，已标记为失败，下次将重试。")

        self.collection.flush()
        print(f"🎉 同步完成！当前库中总实体数: {self.collection.num_entities}")
=======
                batch_texts = chunks[i: i + 10]
                vectors = self.get_embeddings(batch_texts)

                if vectors and len(vectors) == len(batch_texts):
                    try:
                        safe_texts = [t[:3800] for t in batch_texts]
                        self.collection.insert([[file_name] * len(vectors), safe_texts, vectors])
                        # --- 重新加入的入库成功提示 ---
                        print(f"  ✅ 批次 {i // 10 + 1}/{(len(chunks) - 1) // 10 + 1} 成功入库")
                    except Exception as e:
                        print(f"  ❌ Milvus 插入失败: {e}")
                        all_chunks_success = False;
                        break
                else:
                    all_chunks_success = False;
                    break
                time.sleep(0.4)

            if all_chunks_success:
                self._save_progress(file_name)
            else:
                print(f"  ❗ 文件 '{file_name}' 未能完全处理，下次将重试。")

        self.collection.flush()
        print(f"\n🎉 任务圆满完成！当前 Milvus 总实体数: {self.collection.num_entities}")
>>>>>>> Stashed changes


if __name__ == "__main__":
    MY_CONFIG = {
        "GROUP_ID": "2017772342268142382",
        "API_KEY": "sk-cp-xS6pR0b084LM58KHdamilssG8Vhpp9PxNDirB-bc2jiqHIEsVjZvrWZIfoUif1vy7g3g1ttqyqU6X6aFpsiXSg2HJXtM-66HKgQE2Zst6o7gZh3kLV9UQBA",
        "COLLECTION": "legal_ocr_v1",
        "DATA_PATH": "/Volumes/lexar/openclawpdf/legal_md_files",
        "PROGRESS_FILE": "ocr_ingest_progress.json"
    }
    UniversalLegalIngestor(MY_CONFIG).run()