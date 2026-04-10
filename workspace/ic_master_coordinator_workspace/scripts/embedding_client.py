#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding客户端 - 支持多后端
用于SIQ投委会系统的文档向量化

支持后端：
1. 本地模型（sentence-transformers）
2. OpenAI API
3. 阿里云DashScope
4. 硅基流动SiliconFlow
"""

import os
import json
import hashlib
from typing import List, Union, Optional
import numpy as np


class EmbeddingClient:
    """
    Embedding客户端
    
    默认使用本地轻量级模型，支持云端API作为备选
    """
    
    def __init__(self, backend: str = "local", model_name: str = None):
        """
        初始化Embedding客户端
        
        Args:
            backend: 后端类型 (local/openai/dashscope/siliconflow)
            model_name: 模型名称（可选，使用默认）
        """
        self.backend = backend
        self.model_name = model_name or self._get_default_model()
        self.embedding_dim = 1024  # 默认维度，根据模型调整
        
        print(f"✅ Embedding客户端初始化")
        print(f"   后端: {backend}")
        print(f"   模型: {self.model_name}")
        
        if backend == "local":
            self._init_local()
        elif backend == "openai":
            self._init_openai()
        elif backend == "dashscope":
            self._init_dashscope()
        elif backend == "siliconflow":
            self._init_siliconflow()
        else:
            raise ValueError(f"不支持的后端: {backend}")
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        defaults = {
            "local": "BAAI/bge-small-zh-v1.5",  # 轻量级中文模型
            "openai": "text-embedding-ada-002",
            "dashscope": "text-embedding-v2",
            "siliconflow": "BAAI/bge-large-zh-v1.5"
        }
        return defaults.get(self.backend, "BAAI/bge-small-zh-v1.5")
    
    def _init_local(self):
        """初始化本地模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            print(f"   正在加载本地模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"   模型维度: {self.embedding_dim}")
            
        except ImportError:
            print("❌ 请先安装sentence-transformers:")
            print("   pip install sentence-transformers")
            raise
    
    def _init_openai(self):
        """初始化OpenAI API"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("请设置OPENAI_API_KEY环境变量")
        self.api_base = "https://api.openai.com/v1"
        self.embedding_dim = 1536  # ada-002
    
    def _init_dashscope(self):
        """初始化阿里云DashScope"""
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置DASHSCOPE_API_KEY环境变量")
        self.api_base = "https://dashscope.aliyuncs.com/api/v1"
        self.embedding_dim = 1536
    
    def _init_siliconflow(self):
        """初始化硅基流动"""
        self.api_key = os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("请设置SILICONFLOW_API_KEY环境变量")
        self.api_base = "https://api.siliconflow.cn/v1"
        self.embedding_dim = 1024
    
    def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        文本向量化
        
        Args:
            texts: 单个文本或文本列表
        
        Returns:
            向量列表
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if self.backend == "local":
            return self._embed_local(texts)
        elif self.backend == "openai":
            return self._embed_openai(texts)
        elif self.backend == "dashscope":
            return self._embed_dashscope(texts)
        elif self.backend == "siliconflow":
            return self._embed_siliconflow(texts)
    
    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """本地模型向量化"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def _embed_api(self, texts: List[str], api_url: str, headers: dict) -> List[List[float]]:
        """通用API向量化"""
        import requests
        
        embeddings = []
        # API通常有batch限制，分批处理
        batch_size = 16
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            payload = {
                "model": self.model_name,
                "input": batch
            }
            
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            batch_embeddings = [item["embedding"] for item in result["data"]]
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """OpenAI API向量化"""
        return self._embed_api(
            texts,
            f"{self.api_base}/embeddings",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    def _embed_dashscope(self, texts: List[str]) -> List[List[float]]:
        """阿里云DashScope向量化"""
        return self._embed_api(
            texts,
            f"{self.api_base}/services/embeddings/text-embedding/text-embedding",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    def _embed_siliconflow(self, texts: List[str]) -> List[List[float]]:
        """硅基流动向量化"""
        return self._embed_api(
            texts,
            f"{self.api_base}/embeddings",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    def embed_chunks(self, chunks: List[dict]) -> List[dict]:
        """
        批量向量化chunks
        
        Args:
            chunks: [{"id": "...", "text": "...", "metadata": {...}}]
        
        Returns:
            添加了vector字段的chunks
        """
        texts = [chunk["text"] for chunk in chunks]
        
        print(f"🔢 开始向量化: {len(texts)}个chunks")
        
        # 分批处理，避免内存溢出
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.embed(batch)
            all_embeddings.extend(batch_embeddings)
            
            if (i // batch_size + 1) % 10 == 0:
                print(f"   进度: {min(i+batch_size, len(texts))}/{len(texts)}")
        
        # 添加vector到chunks
        for chunk, vector in zip(chunks, all_embeddings):
            chunk["vector"] = vector
        
        print(f"✅ 向量化完成: {len(chunks)}个chunks")
        return chunks


# 便捷函数
def get_embedding_client(backend: str = None) -> EmbeddingClient:
    """
    获取Embedding客户端（自动选择后端）
    
    优先级：
    1. 如果设置了SILICONFLOW_API_KEY，使用硅基流动
    2. 如果设置了OPENAI_API_KEY，使用OpenAI
    3. 如果设置了DASHSCOPE_API_KEY，使用DashScope
    4. 默认使用本地模型
    """
    if backend:
        return EmbeddingClient(backend=backend)
    
    # 自动检测
    if os.getenv("SILICONFLOW_API_KEY"):
        return EmbeddingClient(backend="siliconflow")
    elif os.getenv("OPENAI_API_KEY"):
        return EmbeddingClient(backend="openai")
    elif os.getenv("DASHSCOPE_API_KEY"):
        return EmbeddingClient(backend="dashscope")
    else:
        print("⚠️ 未检测到API Key，使用本地模型（需要下载）")
        return EmbeddingClient(backend="local")


# 使用示例
if __name__ == "__main__":
    # 测试本地模型
    print("\n" + "="*60)
    print("测试Embedding客户端")
    print("="*60)
    
    try:
        # 尝试使用本地模型
        client = EmbeddingClient(backend="local", model_name="BAAI/bge-small-zh-v1.5")
        
        # 测试向量化
        test_texts = [
            "宇树科技是一家机器人公司",
            "财务收入增长了50%",
            "公司估值达到100亿人民币"
        ]
        
        embeddings = client.embed(test_texts)
        
        print(f"\n✅ 向量化成功")
        print(f"   文本数量: {len(test_texts)}")
        print(f"   向量维度: {len(embeddings[0])}")
        print(f"   示例向量: {embeddings[0][:5]}...")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n请安装依赖:")
        print("  pip install sentence-transformers")