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
        """Hybrid search using Reciprocal Rank Fusion with title boost and optimized set operations"""
        query_lower = query.lower()
        bm25_results = self.bm25_index.search(query_lower, limit=limit * 2)
        vector_results = self.vector_index.search(query_lower, limit=limit * 2)
        
        combined_scores = {}
        query_terms = set(query_lower.split())
        
        # Pre-extract important query nouns
        important_query_terms = query_terms & self.IMPORTANT_NOUNS
        unique_base_nouns = set()
        for noun in important_query_terms:
            if noun.endswith('s') and noun[:-1] in self.IMPORTANT_NOUNS:
                unique_base_nouns.add(noun[:-1])
            else:
                unique_base_nouns.add(noun)
        
        # BM25 scores
        for rank, result in enumerate(bm25_results, start=1):
            doc_id = result['id']
            rrf_score = 1.0 / (60 + rank)
            
            title = result.get('content', {}).get('title', '').lower()
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            title_boost = 1.0 + (title_match_count * 0.5)
            
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
            
            title = result.get('content', {}).get('title', '').lower()
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            title_boost = 1.0 + (title_match_count * 0.5)
            
            if doc_id in combined_scores:
                combined_scores[doc_id]['score'] += (1 - self.alpha) * rrf_score * title_boost
                combined_scores[doc_id]['vector_rank'] = rank
                combined_scores[doc_id]['title_boost'] = max(combined_scores[doc_id]['title_boost'], title_boost)
            else:
                combined_scores[doc_id] = {
                    'score': (1 - self.alpha) * rrf_score * title_boost,
                    'result': result,
                    'bm25_rank': None,
                    'vector_rank': rank,
                    'title_boost': title_boost
                }
        
        # Sort and apply strict filters/boosts
        sorted_candidates = sorted(combined_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        final_results = []
        
        for doc_id, data in sorted_candidates:
            title = data['result'].get('content', {}).get('title', '').lower()
            
            if unique_base_nouns:
                # Optimized matching using pre-calculated base nouns
                matched_count = 0
                for base in unique_base_nouns:
                    if base in title or (base + 's') in title:
                        matched_count += 1
                
                match_ratio = matched_count / len(unique_base_nouns)
                if match_ratio >= 1.0:
                    data['score'] *= 2.0
                elif match_ratio > 0:
                    data['score'] *= 0.1
                else:
                    # No noun match, keep score but might be filtered later
                    pass
            
            final_results.append({
                'id': doc_id,
                'score': data['score'],
                'content': data['result']['content'],
                'bm25_rank': data['bm25_rank'],
                'vector_rank': data['vector_rank']
            })
            
            if len(final_results) >= limit + 5: # Get a few extra for final re-sort
                break
        
        # Final re-sort after boosted scores
        final_results.sort(key=lambda x: x['score'], reverse=True)
        return final_results[:limit]
