"""
Catalog Module - Main API Interface

Provides product search and retrieval capabilities using hybrid BM25 + vector search.
"""

from typing import List, Optional, Dict, Any

from .indexing import DatabaseManager, BM25Index, VectorIndex, HybridSearch, ProductDB, ProductSpecDB
from .models import IndexDocument
from .config import index_config


class CatalogIndexer:
    """Main catalog search interface"""
    
    def __init__(self):
        # Initialize database
        self.db_manager = DatabaseManager()
        
        # Initialize BM25 indexes
        self.products_bm25 = BM25Index("products_index", self.db_manager)
        self.specs_bm25 = BM25Index("product_specs_index", self.db_manager)
        
        # Initialize vector indexes
        self.products_vector = VectorIndex("products_index", index_config.embedding_model)
        self.specs_vector = VectorIndex("product_specs_index", index_config.embedding_model)
        
        # Initialize hybrid searchers
        self.products_search = HybridSearch(
            self.products_bm25,
            self.products_vector,
            index_config.hybrid_alpha
        )
        self.specs_search = HybridSearch(
            self.specs_bm25,
            self.specs_vector,
            index_config.hybrid_alpha
        )
        
        # Load existing indexes
        self.products_bm25.load()
        self.specs_bm25.load()
        
        # Check if we have products loaded
        self.products = self._get_all_products()
        product_count = len(self.products)
        
        if product_count > 0:
            print(f"[Catalog] Initialized successfully with {product_count} products")
        else:
            print("[Catalog] WARNING: No products in index. Run 'python -m app.modules.assistant.cli index-catalog' to index products")
        
        print("[Catalog] Ready for searches")
    
    # Public API Methods
    
    def searchProducts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search products using hybrid search
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of product results with scores
        """
        return self.products_search.search(query, limit)
    
    def searchSpecs(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search product specifications using hybrid search
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of specification results with scores
        """
        return self.specs_search.search(query, limit)
    
    def getProductById(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get product by SKU
        
        Args:
            sku: Product SKU identifier
            
        Returns:
            Product dictionary or None if not found
        """
        session = self.db_manager.get_session()
        try:
            product = session.query(ProductDB).filter_by(sku=sku).first()
            return product.to_dict() if product else None
        finally:
            session.close()
    
    def getProductsByIds(self, skus: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple products by their SKUs in a single query.
        
        Args:
            skus: List of product SKUs
            
        Returns:
            List of product dictionaries
        """
        if not skus:
            return []
            
        session = self.db_manager.get_session()
        try:
            products = session.query(ProductDB).filter(ProductDB.sku.in_(skus)).all()
            return [p.to_dict() for p in products]
        finally:
            session.close()
    
    def getSpecsForProduct(self, sku: str) -> List[Dict[str, Any]]:
        """
        Get all specifications for a product
        
        Args:
            sku: Product SKU identifier
            
        Returns:
            List of specification dictionaries
        """
        session = self.db_manager.get_session()
        try:
            specs = session.query(ProductSpecDB).filter_by(sku=sku).all()
            return [spec.to_dict() for spec in specs]
        finally:
            session.close()
    
    # Index Building Methods (for manual rebuilds)
    
    def addProducts(self, products: List[Dict[str, Any]]) -> None:
        """
        Add products to the index
        
        Args:
            products: List of product dictionaries with keys:
                - sku (required)
                - title (required)
                - handle, price, currency, vendor, tags, image_url, description
        """
        # Deduplicate products by SKU before indexing
        seen_skus = set()
        documents = []
        for product in products:
            sku = product.get('sku')
            if not sku or sku in seen_skus:
                continue
            seen_skus.add(sku)
            
            tags = product.get('tags', [])
            if not isinstance(tags, list):
                tags = []
            option_values = product.get('option_values', []) or []
            if not isinstance(option_values, list):
                option_values = []
            content_parts = [
                product.get('title', ''),
                ' '.join(tags),
                product.get('description', ''),
                product.get('vendor', ''),
                product.get('category', ''),
                product.get('product_type', ''),
                ' '.join(option_values)
            ]
            content = " ".join([part for part in content_parts if part])
            
            doc = IndexDocument(
                id=sku,
                content=content,
                metadata=product
            )
            documents.append(doc)
        
        print(f"[Catalog] Indexing {len(documents)} unique products (from {len(products)} total)")
        
        self.products_bm25.add_documents(documents)
        self.products_bm25.save()
        
        self.products_vector.add_documents(documents)
        
        print(f"[Catalog] Added {len(documents)} products to index")
    
    def addSpecs(self, specs: List[Dict[str, Any]]) -> None:
        """
        Add product specifications to the index
        
        Args:
            specs: List of spec dictionaries with keys:
                - sku (required)
                - section (required)
                - spec_text (required)
                - attributes (optional)
        """
        documents = []
        for idx, spec in enumerate(specs):
            doc = IndexDocument(
                id=f"{spec['sku']}_{spec['section']}_{idx}",
                content=spec['spec_text'],
                metadata={
                    'sku': spec['sku'],
                    'section': spec['section'],
                    'attributes': spec.get('attributes', {})
                }
            )
            documents.append(doc)
        
        self.specs_bm25.add_documents(documents)
        self.specs_bm25.save()
        
        self.specs_vector.add_documents(documents)
        
        print(f"[Catalog] Added {len(documents)} specs to index")
    
    def clearAll(self) -> None:
        """Clear all indexes and database"""
        self.db_manager.clear_all()
        self.products_bm25.clear()
        self.products_vector.clear()
        self.specs_bm25.clear()
        self.specs_vector.clear()
        
        print("[Catalog] Cleared all indexes")
    
    def _get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products from database"""
        session = self.db_manager.get_session()
        try:
            products = session.query(ProductDB).all()
            return [p.to_dict() for p in products]
        finally:
            session.close()
    
    def get_product_count(self) -> int:
        """Get total number of indexed products"""
        return len(self.products)
