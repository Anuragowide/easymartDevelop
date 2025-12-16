"""
Configuration for Catalog Index Module

All paths are relative to backend-python root for monorepo structure.
"""

import os
from pathlib import Path
from dataclasses import dataclass


# Get backend-python root directory
BACKEND_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DATA_DIR = BACKEND_ROOT / "data"


@dataclass
class IndexConfig:
    """Indexing configuration with backend-relative paths"""
    
    # Embedding model (local, no API key needed)
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # BM25 parameters
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    
    # Hybrid search weight (0.5 = equal weight)
    hybrid_alpha: float = 0.5
    
    # Storage paths (relative to backend-python root)
    db_path: Path = DATA_DIR / "easymart.db"
    bm25_dir: Path = DATA_DIR / "bm25"
    chroma_dir: Path = DATA_DIR / "chromadb"
    
    # RRF parameter for hybrid search
    rrf_k: int = 60


# Global config instance
index_config = IndexConfig()


# Ensure directories exist
index_config.bm25_dir.mkdir(parents=True, exist_ok=True)
index_config.chroma_dir.mkdir(parents=True, exist_ok=True)
