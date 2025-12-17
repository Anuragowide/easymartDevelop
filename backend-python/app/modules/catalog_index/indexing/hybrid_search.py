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
        
        # Extract important nouns from query (with singular/plural normalization)
        important_query_terms = query_terms & self.IMPORTANT_NOUNS
        
        # Normalize to base forms for better matching
        # Map plural to singular for consistent matching
        noun_bases = {}
        for noun in important_query_terms:
            if noun.endswith('s') and noun[:-1] in self.IMPORTANT_NOUNS:
                noun_bases[noun] = noun[:-1]  # chairs -> chair
            elif noun + 's' in self.IMPORTANT_NOUNS:
                noun_bases[noun] = noun  # chair stays chair
            else:
                noun_bases[noun] = noun
        
        # Get unique base nouns (e.g., {chair, locker} not {chair, chairs, locker, lockers})
        unique_base_nouns = set(noun_bases.values())
        
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
            
            # Check if important query nouns appear in title (with singular/plural flexibility)
            if unique_base_nouns:
                # Check how many base nouns are matched in the title
                matched_bases = set()
                for base_noun in unique_base_nouns:
                    # Check for both singular and plural forms in title
                    if base_noun in title or (base_noun + 's') in title or base_noun in ' '.join(title_words):
                        matched_bases.add(base_noun)
                
                # STRICT: Require ALL base nouns to be present
                match_ratio = len(matched_bases) / len(unique_base_nouns) if unique_base_nouns else 0
                has_important_match = match_ratio >= 1.0  # 100% required
                
                # BOOST: If ALL nouns match, boost score
                if len(matched_bases) == len(unique_base_nouns):
                    result_item['score'] *= 2.0
                
                # PENALTY: If some but not all nouns match, heavily penalize
                elif match_ratio > 0 and match_ratio < 1.0:
                    result_item['score'] *= 0.1  # Reduce to 10% for partial matches
            else:
                # If no important nouns, require ANY term match
                has_important_match = len(query_terms & title_words) > 0
            
            # Only add if has required match
            if has_important_match:
                final_results.append(result_item)
            elif len(final_results) < 2:  # Only as fallback if we have < 2 results
                final_results.append(result_item)
            
            if len(final_results) >= limit:
                break
        
        # Re-sort after applying strict boosts
        final_results = sorted(final_results, key=lambda x: x['score'], reverse=True)
        
        return final_results[:limit]
