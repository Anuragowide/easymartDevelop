"""
BM25 Keyword Search Implementation

Uses rank-bm25 library for production-ready keyword search with enhanced tokenization.
"""

from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import pickle
import re
from pathlib import Path

from ..models import IndexDocument
from .database import DatabaseManager, ProductDB, ProductSpecDB
from ..config import index_config


# Stop words to filter out (common words with low information content)
STOP_WORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
    'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'will', 'with',
    'too', 'also', 'just', 'very', 'me', 'show', 'find', 'get', 'give', 'want',
    'need', 'looking', 'search', 'please', 'can', 'you', 'i', 'we', 'they', 'this',
    'any', 'some', 'have', 'what', 'which', 'where', 'when', 'how', 'would', 'could'
}

# Important product terms that should never be filtered (even if common)
PRODUCT_KEYWORDS = {
    # Furniture types
    'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas', 'bed', 'beds',
    'locker', 'lockers', 'cabinet', 'cabinets', 'shelf', 'shelves', 'storage',
    'stool', 'stools', 'bench', 'benches', 'wardrobe', 'wardrobes', 'drawer', 'drawers',
    'ottoman', 'ottomans', 'rack', 'racks', 'stand', 'stands', 'couch', 'recliner',
    'lamp', 'lamps', 'rug', 'rugs', 'mirror', 'mirrors', 'bookcase', 'bookshelf',
    # Room types
    'office', 'gaming', 'computer', 'dining', 'bedroom', 'living', 'outdoor', 'patio',
    'kitchen', 'bathroom', 'kids', 'children', 'guest',
    # Materials and styles
    'ergonomic', 'executive', 'mesh', 'leather', 'fabric', 'wood', 'metal', 'glass',
    'plastic', 'velvet', 'modern', 'rustic', 'contemporary', 'vintage',
    # Colors (common product attributes)
    'black', 'white', 'brown', 'grey', 'gray', 'blue', 'red', 'green', 'beige',
    # Quality/price descriptors
    'premium', 'luxury', 'budget', 'affordable', 'cheap'
}


class BM25Index:
    """Production BM25 text-based indexing with enhanced tokenization and persistence"""
    
    def __init__(self, index_name: str, db_manager: DatabaseManager):
        self.index_name = index_name
        self.db_manager = db_manager
        self.index_path = index_config.bm25_dir / f"{index_name}.pkl"
        
        self.bm25: BM25Okapi = None
        self.doc_ids: List[str] = []
        
        print(f"[BM25] Initialized index: {index_name}")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Enhanced tokenization for BM25 with phrase preservation and stop word filtering.
        
        Improvements:
        - Preserves important bigrams (e.g., "gaming chair" stays together)
        - Filters stop words while keeping product keywords
        - Handles hyphenated words
        - Better number handling
        """
        text = text.lower()
        
        # Extract potential bigrams/phrases first
        bigrams = []
        words = re.findall(r'\b\w+\b', text)
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            # Keep bigram if both words are product keywords
            if words[i] in PRODUCT_KEYWORDS or words[i+1] in PRODUCT_KEYWORDS:
                bigrams.append(bigram)
        
        # Regular tokenization
        tokens = re.findall(r'\b\w+\b', text)
        
        # Filter out stop words, keep product keywords and longer words
        filtered_tokens = [
            t for t in tokens 
            if (len(t) > 2 and t not in STOP_WORDS) or t in PRODUCT_KEYWORDS
        ]
        
        # Combine individual tokens with bigrams
        all_tokens = filtered_tokens + bigrams
        
        return all_tokens
    
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
                        compare_at_price=doc.metadata.get('compare_at_price'),
                        currency=doc.metadata.get('currency', 'USD'),
                        image_url=doc.metadata.get('image_url', ''),
                        product_url=doc.metadata.get('product_url', ''),
                        vendor=doc.metadata.get('vendor', ''),
                        tags=doc.metadata.get('tags', []),
                        description=doc.metadata.get('description', ''),
                        search_content=doc.content,
                        inventory_quantity=doc.metadata.get('inventory_quantity', 0),
                        category=doc.metadata.get('category'),
                        product_type=doc.metadata.get('product_type'),
                        status=doc.metadata.get('status'),
                        options_json=doc.metadata.get('options'),
                        variants_json=doc.metadata.get('variants'),
                        images_json=doc.metadata.get('images'),
                        available=int(bool(doc.metadata.get('available', True))),
                        inventory_managed=int(bool(doc.metadata.get('inventory_managed', False))),
                        barcode=doc.metadata.get('barcode')
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
        """Search using BM25 with optimized batch database retrieval.
        
        Optimized for large catalogs (2000+ products) with:
        - Efficient score filtering
        - Batch database queries
        - Minimum score threshold
        """
        if self.bm25 is None:
            self.load()
            if self.bm25 is None:
                return []
        
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            print(f"[BM25] Warning: No valid tokens extracted from query: '{query}'")
            return []
        
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top indices where score > 0.01 (filter out very low scores)
        MIN_SCORE = 0.01
        top_indices = sorted(
            [i for i in range(len(scores)) if scores[i] > MIN_SCORE],
            key=lambda i: scores[i], 
            reverse=True
        )[:limit]
        
        if not top_indices:
            return []
            
        doc_ids = [self.doc_ids[idx] for idx in top_indices]
        results_map = {}
        
        session = self.db_manager.get_session()
        try:
            # Batch query instead of loop (Fixes N+1 problem)
            if self.index_name == "products_index":
                products = session.query(ProductDB).filter(ProductDB.sku.in_(doc_ids)).all()
                results_map = {p.sku: p.to_dict() for p in products}
            elif self.index_name == "product_specs_index":
                specs = session.query(ProductSpecDB).filter(ProductSpecDB.id.in_(doc_ids)).all()
                results_map = {s.id: s.to_dict() for s in specs}
        finally:
            session.close()
            
        # Re-assemble results in correct order with scores
        results = []
        for idx in top_indices:
            doc_id = self.doc_ids[idx]
            if doc_id in results_map:
                results.append({
                    'id': doc_id,
                    'score': float(scores[idx]),
                    'content': results_map[doc_id],
                    'type': 'product' if self.index_name == "products_index" else 'spec'
                })
        
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
        
        try:
            with open(self.index_path, 'rb') as f:
                index_data = pickle.load(f)
                self.bm25 = index_data['bm25']
                self.doc_ids = index_data['doc_ids']
                self.corpus = index_data.get('corpus', [])
            
            print(f"[BM25] Loaded index from {self.index_path}")
        except (EOFError, pickle.UnpicklingError, Exception) as e:
            print(f"[BM25] Error loading index from {self.index_path}: {e}")
            print(f"[BM25] Index file may be corrupted. Deleting and will rebuild on next sync.")
            
            # Delete corrupted file
            if self.index_path.exists():
                self.index_path.unlink()
            
            # Reset state
            self.bm25 = None
            self.doc_ids = []
            self.corpus = []
    
    def clear(self) -> None:
        """Clear the index"""
        self.bm25 = None
        self.doc_ids = []
        
        if self.index_path.exists():
            self.index_path.unlink()
