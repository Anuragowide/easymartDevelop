"""
Hybrid Search - Combines BM25 and Vector Search

Uses Reciprocal Rank Fusion (RRF) to merge results.
"""

from typing import List, Dict, Any

from .bm25_index import BM25Index
from .vector_index import VectorIndex


class HybridSearch:
    """Combines BM25 and Vector search using RRF"""
    
    # Common furniture/product nouns that should match in title
    IMPORTANT_NOUNS = {
        'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas',
        'bed', 'beds', 'locker', 'lockers', 'cabinet', 'cabinets', 'shelf', 'shelves',
        'storage', 'stool', 'stools', 'bench', 'benches', 'wardrobe', 'wardrobes',
        'drawer', 'drawers', 'ottoman', 'ottomans', 'rack', 'racks', 'stand', 'stands'
    }
    
    def __init__(self, bm25_index: BM25Index, vector_index: VectorIndex, alpha: float = 0.5):
        self.bm25_index = bm25_index
        self.vector_index = vector_index
        self.alpha = alpha
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Hybrid search using Reciprocal Rank Fusion with title boost"""
        bm25_results = self.bm25_index.search(query, limit=limit * 2)
        vector_results = self.vector_index.search(query, limit=limit * 2)
        
        combined_scores = {}
        query_terms = set(query.lower().split())
        
        # BM25 scores
        for rank, result in enumerate(bm25_results, start=1):
            doc_id = result['id']
            rrf_score = 1.0 / (60 + rank)
            
            # Boost score if query terms appear in title
            title = result.get('content', {}).get('title', '').lower()
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            title_boost = 1.0 + (title_match_count * 0.5)  # +50% per matching word
            
            combined_scores[doc_id] = {
                'score': self.alpha * rrf_score * title_boost,
                'result': result,
                'bm25_rank': rank,
                'vector_rank': None,
                'title_boost': title_boost
            }
        
        # Vector scores
        for rank, result in enumerate(vector_results, start=1):
            doc_id = result['id']
            rrf_score = 1.0 / (60 + rank)
            
            # Boost score if query terms appear in title
            title = result.get('content', {}).get('title', '').lower()
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            title_boost = 1.0 + (title_match_count * 0.5)  # +50% per matching word
            
            if doc_id in combined_scores:
                combined_scores[doc_id]['score'] += (1 - self.alpha) * rrf_score * title_boost
                combined_scores[doc_id]['vector_rank'] = rank
                # Update boost to max of both
                combined_scores[doc_id]['title_boost'] = max(
                    combined_scores[doc_id].get('title_boost', 1.0),
                    title_boost
                )
            else:
                combined_scores[doc_id] = {
                    'score': (1 - self.alpha) * rrf_score * title_boost,
                    'result': result,
                    'bm25_rank': None,
                    'vector_rank': rank,
                    'title_boost': title_boost
                }
        
        # Sort by score
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        # Format results with stricter filtering
        final_results = []
        
        # Find important nouns in query
        important_query_terms = query_terms & self.IMPORTANT_NOUNS
        
        for doc_id, data in sorted_results[:limit * 3]:  # Get more for filtering
            result_item = {
                'id': doc_id,
                'score': data['score'],
                'content': data['result']['content'],
                'bm25_rank': data['bm25_rank'],
                'vector_rank': data['vector_rank']
            }
            
            title = data['result'].get('content', {}).get('title', '').lower()
            title_words = set(title.split())
            
            # Check if important query terms (nouns) appear in title
            if important_query_terms:
                # If query has important nouns, require at least ONE in title
                has_important_match = len(important_query_terms & title_words) > 0
            else:
                # If no important nouns in query, require ANY term match
                has_important_match = len(query_terms & title_words) > 0
            
            # Only add if has required match OR we don't have enough results yet
            if has_important_match or len(final_results) < 3:
                final_results.append(result_item)
            
            if len(final_results) >= limit:
                break
        
        return final_results
