"""
Vector Semantic Search Implementation

Uses sentence-transformers + ChromaDB for semantic search.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import json

from ..models import IndexDocument
from ..config import index_config


class VectorIndex:
    """Production vector embedding-based indexing with ChromaDB"""
    
    def __init__(self, index_name: str, embedding_model: str = "all-MiniLM-L6-v2"):
        self.index_name = index_name
        self.embedding_model_name = embedding_model
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=str(index_config.chroma_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        self.collection = self.client.get_or_create_collection(
            name=index_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"[Vector] Loading embedding model: {embedding_model}")
        self.model = SentenceTransformer(embedding_model)
        print(f"[Vector] Initialized index: {index_name}")
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert lists and nested dicts to JSON strings for ChromaDB"""
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                sanitized[key] = json.dumps(value)
            elif value is None:
                sanitized[key] = ""
            else:
                sanitized[key] = value
        return sanitized
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        return embeddings.tolist()
    
    def add_documents(self, documents: List[IndexDocument], batch_size: int = 100) -> None:
        """Add documents to vector index"""
        if not documents:
            return
        
        print(f"[Vector] Adding {len(documents)} documents to {self.index_name}")
        
        for i in tqdm(range(0, len(documents), batch_size), desc="Indexing"):
            batch = documents[i:i + batch_size]
            
            ids = [doc.id for doc in batch]
            texts = [doc.content for doc in batch]
            metadatas = [self._sanitize_metadata(doc.metadata) for doc in batch]
            
            embeddings = self._generate_embeddings(texts)
            
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
        
        print(f"[Vector] Added {len(documents)} documents")
    
    def search(self, query: str, limit: int = 5, where: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search using vector similarity"""
        query_embedding = self._generate_embeddings([query])[0]
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    'id': doc_id,
                    'score': float(results['distances'][0][i]),
                    'content': results['metadatas'][0][i],
                    'text': results['documents'][0][i],
                    'type': 'vector'
                })
        
        return formatted_results
    
    def get_count(self) -> int:
        """Get document count"""
        return self.collection.count()
    
    def clear(self) -> None:
        """Clear the index"""
        self.client.delete_collection(name=self.index_name)
        self.collection = self.client.get_or_create_collection(
            name=self.index_name,
            metadata={"hnsw:space": "cosine"}
        )
