"""
BM25 Keyword Search Implementation

Uses rank-bm25 library for production-ready keyword search.
"""

from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import pickle
import re
from pathlib import Path

from ..models import IndexDocument
from .database import DatabaseManager, ProductDB, ProductSpecDB
from ..config import index_config


class BM25Index:
    """Production BM25 text-based indexing with persistence"""
    
    def __init__(self, index_name: str, db_manager: DatabaseManager):
        self.index_name = index_name
        self.db_manager = db_manager
        self.index_path = index_config.bm25_dir / f"{index_name}.pkl"
        
        self.bm25: BM25Okapi = None
        self.doc_ids: List[str] = []
        
        print(f"[BM25] Initialized index: {index_name}")
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25"""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        tokens = [t for t in tokens if len(t) > 2]
        return tokens
    
    def add_documents(self, documents: List[IndexDocument]) -> None:
        """Add documents to BM25 index and database"""
        if not documents:
            return
        
        session = self.db_manager.get_session()
        
        try:
            corpus = []
            doc_ids = []
            
            for doc in documents:
                tokens = self._tokenize(doc.content)
                corpus.append(tokens)
                doc_ids.append(doc.id)
                
                if self.index_name == "products_index":
                    product = ProductDB(
                        sku=doc.id,
                        handle=doc.metadata.get('handle', ''),
                        title=doc.metadata.get('title', ''),
                        price=doc.metadata.get('price', 0.0),
                        currency=doc.metadata.get('currency', 'USD'),
                        image_url=doc.metadata.get('image_url', ''),
                        product_url=doc.metadata.get('product_url', ''),
                        vendor=doc.metadata.get('vendor', ''),
                        tags=doc.metadata.get('tags', []),
                        description=doc.metadata.get('description', ''),
                        search_content=doc.content,
                        inventory_quantity=doc.metadata.get('inventory_quantity', 0)
                    )
                    session.merge(product)
                
                elif self.index_name == "product_specs_index":
                    spec = ProductSpecDB(
                        id=doc.id,
                        sku=doc.metadata.get('sku', ''),
                        section=doc.metadata.get('section', ''),
                        spec_text=doc.content,
                        attributes_json=doc.metadata.get('attributes', {})
                    )
                    session.merge(spec)
            
            session.commit()
            
            if self.bm25 is None:
                self.bm25 = BM25Okapi(corpus)
                self.doc_ids = doc_ids
            else:
                # BM25Okapi doesn't expose corpus directly in all versions, 
                # but we can reconstruct it or just re-initialize with full list if we had it.
                # However, since we don't store the full corpus in memory persistently (only in pickle),
                # we rely on what's loaded.
                # If 'corpus' attribute is missing, we might need to store it ourselves.
                
                # Fix: Store corpus explicitly in the class
                if not hasattr(self, 'corpus'):
                    self.corpus = corpus
                else:
                    self.corpus.extend(corpus)
                
                self.bm25 = BM25Okapi(self.corpus)
                self.doc_ids.extend(doc_ids)
            
            # Ensure corpus is stored for next time
            if not hasattr(self, 'corpus'):
                self.corpus = corpus
            
            print(f"[BM25] Added {len(documents)} documents to {self.index_name}")
            
        finally:
            session.close()
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search using BM25"""
        if self.bm25 is None:
            self.load()
            if self.bm25 is None:
                return []
        
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:limit]
        
        session = self.db_manager.get_session()
        results = []
        
        try:
            for idx in top_indices:
                if scores[idx] <= 0:
                    continue
                
                doc_id = self.doc_ids[idx]
                
                if self.index_name == "products_index":
                    product = session.query(ProductDB).filter_by(sku=doc_id).first()
                    if product:
                        results.append({
                            'id': doc_id,
                            'score': float(scores[idx]),
                            'content': product.to_dict(),
                            'type': 'product'
                        })
                
                elif self.index_name == "product_specs_index":
                    spec = session.query(ProductSpecDB).filter_by(id=doc_id).first()
                    if spec:
                        results.append({
                            'id': doc_id,
                            'score': float(scores[idx]),
                            'content': spec.to_dict(),
                            'type': 'spec'
                        })
        
        finally:
            session.close()
        
        return results
    
    def save(self) -> None:
        """Save BM25 index to disk"""
        if self.bm25 is None:
            return
        
        # Save corpus as well
        index_data = {
            'bm25': self.bm25, 
            'doc_ids': self.doc_ids,
            'corpus': getattr(self, 'corpus', [])
        }
        
        with open(self.index_path, 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"[BM25] Saved index to {self.index_path}")
    
    def load(self) -> None:
        """Load BM25 index from disk"""
        if not self.index_path.exists():
            return
        
        with open(self.index_path, 'rb') as f:
            index_data = pickle.load(f)
            self.bm25 = index_data['bm25']
            self.doc_ids = index_data['doc_ids']
            self.corpus = index_data.get('corpus', [])
        
        print(f"[BM25] Loaded index from {self.index_path}")
        
        self.bm25 = index_data['bm25']
        self.doc_ids = index_data['doc_ids']
        
        print(f"[BM25] Loaded index from {self.index_path}")
    
    def clear(self) -> None:
        """Clear the index"""
        self.bm25 = None
        self.doc_ids = []
        
        if self.index_path.exists():
            self.index_path.unlink()
