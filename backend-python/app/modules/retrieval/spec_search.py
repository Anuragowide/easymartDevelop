"""
Specification Search Wrapper

High-level interface for product specification search.
Used for answering detailed questions about products.
"""

import asyncio
from typing import List, Dict, Any, Optional
from app.modules.catalog_index import CatalogIndexer


class SpecSearcher:
    """
    High-level specification search interface.
    Wraps CatalogIndexer spec search with additional features.
    """
    
    def __init__(self):
        self.catalog = CatalogIndexer()
    
    async def search(
        self, 
        query: str, 
        limit: int = 5,
        sku: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search product specifications.
        
        Args:
            query: Search query (e.g., "dimensions", "material", "weight")
            limit: Maximum number of results
            sku: Optional SKU to limit search to specific product
        
        Returns:
            List of specification results with scores
        
        Example:
            >>> searcher = SpecSearcher()
            >>> results = await searcher.search("what are the dimensions?")
            >>> results = await searcher.search("material", sku="WALLET-001")
        """
        
        # Get raw search results from catalog
        results = await asyncio.to_thread(self.catalog.searchSpecs, query, limit=limit * 2)
        
        # Filter by SKU if provided
        if sku:
            results = [
                r for r in results 
                if r.get("content", {}).get("sku") == sku
            ]
        
        # Return top N results
        return results[:limit]
    
    async def get_specs_for_product(self, sku: str) -> List[Dict[str, Any]]:
        """
        Get all specifications for a product.
        
        Args:
            sku: Product SKU
        
        Returns:
            List of all specs for the product
        """
        return await asyncio.to_thread(self.catalog.getSpecsForProduct, sku)
    
    async def get_spec_section(
        self, 
        sku: str, 
        section: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific section of product specs.
        
        Args:
            sku: Product SKU
            section: Spec section name (dimensions, material, etc.)
        
        Returns:
            Spec dictionary for the section or None
        
        Example:
            >>> searcher = SpecSearcher()
            >>> dimensions = await searcher.get_spec_section("WALLET-001", "dimensions")
        """
        specs = await self.get_specs_for_product(sku)
        
        for spec in specs:
            if spec.get("section", "").lower() == section.lower():
                return spec
        
        return None
    
    async def answer_question(
        self, 
        question: str, 
        sku: Optional[str] = None
    ) -> str:
        """
        Answer a question about product specifications.
        
        Args:
            question: User question (e.g., "How big is the wallet?")
            sku: Optional product SKU
        
        Returns:
            Answer text
        
        TODO: Implement LLM-based answer generation from spec search results
        """
        
        # Search for relevant specs
        results = await self.search(question, limit=3, sku=sku)
        
        if not results:
            return "I couldn't find any information about that."
        
        # Combine top results
        answers = []
        for res in results:
            spec = res.get("content", {})
            text = spec.get("spec_text", "")
            if text and text not in answers:
                answers.append(text)
        
        return "\n\n".join(answers)
