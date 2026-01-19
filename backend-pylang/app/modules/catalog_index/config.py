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
    
    # BM25 parameters (tuned for e-commerce)
    bm25_k1: float = 1.2  # Slightly lower for shorter product titles
    bm25_b: float = 0.75
    
    # Hybrid search weight (0.6 = slight preference for keyword search)
    hybrid_alpha: float = 0.6
    
    # Storage paths (relative to backend-python root)
    db_path: Path = DATA_DIR / "easymart.db"
    bm25_dir: Path = DATA_DIR / "bm25"
    chroma_dir: Path = DATA_DIR / "chromadb"
    
    # RRF parameter for hybrid search
    rrf_k: int = 60
    
    # Search limits for large catalogs (2000+ products)
    search_candidate_multiplier: int = 8  # Get 8x limit candidates for filtering
    max_search_candidates: int = 100  # Cap total candidates to search
    min_search_results: int = 3  # Minimum results to return with fallback


# Global config instance
index_config = IndexConfig()


# Ensure directories exist
index_config.bm25_dir.mkdir(parents=True, exist_ok=True)
index_config.chroma_dir.mkdir(parents=True, exist_ok=True)
