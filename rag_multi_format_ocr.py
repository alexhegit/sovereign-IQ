import os
import re
import time
import json
import requests
import numpy as np
from typing import List, Set

# 解析与 OCR
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

# 彻底解决 macOS 警告
os.environ["OBJC_DISABLE_INITIALIZE_FOR_SAFETY"] = "YES"


class UltimateLegalIngestor:
    def __init__(self, collection_name: str, group_id: str, api_key: str, progress_file: str):
        self.collection_name = collection_name
        self.group_id = group_id
        self.api_key = api_key
        # 强制将块限制在 800 字符，确保即便加上文件名等元数据也绝对不超标
        self.char_limit = 800
        self.vector_dim = 1536
        self.progress_file = progress_file
        self._ocr = None

        connections.connect("default", host="localhost", port="19530")
        self.collection = self._ensure_collection_exists()
        self.collection.load()

        self.api_url = f"https://api.minimax.chat/v1/embeddings?GroupId={self.group_id}"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @property
    def ocr(self):
        if self._ocr is None:
            print("⏳ 正在加载 PaddleOCR 模型 (需连接网络)...")
            self._ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        return self._ocr

    def _ensure_collection_exists(self) -> Collection:
        if utility.has_collection(self.collection_name):
            print(f"ℹ️ 集合 '{self.collection_name}' 已就绪。")
            return Collection(self.collection_name)

        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.vector_dim)
        ]
        schema = CollectionSchema(fields, "法律法规向量数据库")
        col = Collection(self.collection_name, schema)
        col.create_index("vector", {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
        return col

    def _extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif ext == '.docx':
                text = "\n".join([p.text for p in Document(file_path).paragraphs])
            elif ext == '.pptx':
                text = "\n".join(
                    [s.text for sl in Presentation(file_path).slides for s in sl.shapes if hasattr(s, "text")])
            elif ext == '.pdf':
                reader = PdfReader(file_path)
                text = "\n".join([p.extract_text() or "" for p in reader.pages])
                if len(text.strip()) < 50:
                    print(f"🔍 检测到扫描件或空文件，尝试 OCR: {os.path.basename(file_path)}")
                    images = convert_from_path(file_path, dpi=150)
                    ocr_res = []
                    for img in images:
                        res = self.ocr.ocr(np.array(img), cls=True)
                        if res and res[0]:
                            ocr_res.append(" ".join([line[1][0] for line in res[0]]))
                    text = "\n".join(ocr_res)
        except Exception as e:
            print(f"⚠️ 解析失败 {file_path}: {e}")
        return text

    def _robust_split(self, text: str) -> List[str]:
        """[保底物理切分] 确保任何块长度都严格受控"""
        text = text.replace('\0', '').strip()
        if not text: return []
        # 直接暴力切分，不留任何溢出可能
        return [text[i: i + self.char_limit] for i in range(0, len(text), self.char_limit)]

    def _load_progress(self) -> Set[str]:
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                try:
                    return set(json.load(f))
                except:
                    return set()
        return set()

    def _save_progress(self, file_name: str):
        processed = self._load_progress()
        processed.add(file_name)
        with open(self.progress_file, 'w') as f: json.dump(list(processed), f)

    def process_directory(self, dir_path: str):
        if not os.path.exists(dir_path):
            print(f"❌ 路径错误：无法访问 {dir_path}");
            return

        valid_exts = {'.pdf', '.docx', '.pptx', '.txt', '.md'}
        all_files = sorted([f for f in os.listdir(dir_path) if os.path.splitext(f)[1].lower() in valid_exts])

        print(f"📂 文件夹内共发现 {len(all_files)} 个符合格式的文件")

        processed = self._load_progress()
        pending = [f for f in all_files if f not in processed]

        if not pending:
            print("✨ 进度显示所有文件已处理。如果想重新运行，请手动删除进度文件。")
            return

        print(f"🚀 准备处理 {len(pending)} 个新文件...")

        for file_name in tqdm(pending, desc="正在入库"):
            file_path = os.path.join(dir_path, file_name)
            content = self._extract_text(file_path)

            # 物理截断
            chunks = self._robust_split(content)
            print(f"📝 文件 '{file_name}' 被切分为 {len(chunks)} 个片段")

            for i in range(0, len(chunks), 10):
                batch_texts = chunks[i: i + 10]
                # 发送向量化请求
                try:
                    res = requests.post(self.api_url, headers=self.headers,
                                        json={"model": "embo-01", "texts": batch_texts, "type": "db"}, timeout=60)
                    vectors = res.json().get("vectors", [])
                    if vectors:
                        # 确保插入数据库的文本绝对不超过 4000
                        safe_texts = [t[:3800] for t in batch_texts]
                        self.collection.insert([[file_name] * len(vectors), safe_texts, vectors])
                    time.sleep(0.5)
                except Exception as e:
                    print(f"❌ 批次处理失败: {e}")

            self._save_progress(file_name)

        self.collection.flush()
        print(f"🎉 任务圆满完成！当前 Milvus 总实体数: {self.collection.num_entities}")


if __name__ == "__main__":
    CONFIG = {
        "GROUP_ID": "201777234226814****",
        "API_KEY": "sk-cp-xS6pR0b084LM58KHdamilssG8Vhpp9PxNDirB-bc2jiqHIEsVjZvrWZIfoUif1vy7g3g1ttqyqU6X6aFpsiXSg2HJXtM-66HKgQE2Zst6o7gZh3kLV9****",
        "COLLECTION": "legal_ocr_v1",
        "DATA_PATH": "/Volumes/lexar/openclawpdf/zhidu",
        "PROGRESS_FILE": "ocr_ingest_progress.json"
    }
    ingestor = UltimateLegalIngestor(CONFIG["COLLECTION"], CONFIG["GROUP_ID"], CONFIG["API_KEY"],
                                     CONFIG["PROGRESS_FILE"])
    ingestor.process_directory(CONFIG["DATA_PATH"])
