"""
Hybrid Search - Combines BM25 and Vector Search

Uses Reciprocal Rank Fusion (RRF) to merge results with enhanced phrase matching.
"""

from typing import List, Dict, Any
import re

from .bm25_index import BM25Index
from .vector_index import VectorIndex


class HybridSearch:
    """Combines BM25 and Vector search using RRF with phrase boost"""
    
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
    
    def _calculate_phrase_score(self, query: str, title: str, description: str) -> float:
        """
        Calculate phrase matching score.
        
        Boosts results where:
        - Exact phrase appears in title (highest boost)
        - All query terms appear in title (high boost)
        - Exact phrase appears in description (medium boost)
        - All query terms appear in description (low boost)
        """
        query_lower = query.lower().strip()
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Exact phrase in title = 5x boost
        if query_lower in title_lower:
            return 5.0
        
        # All words in title = 3x boost
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        title_words = set(re.findall(r'\b\w+\b', title_lower))
        if query_words.issubset(title_words):
            return 3.0
        
        # Exact phrase in description = 2x boost
        if query_lower in desc_lower:
            return 2.0
        
        # All words in description = 1.5x boost
        desc_words = set(re.findall(r'\b\w+\b', desc_lower))
        if query_words.issubset(desc_words):
            return 1.5
        
        # Partial match in title (at least 50% of query words)
        title_match_count = len(query_words & title_words)
        if title_match_count > 0:
            match_ratio = title_match_count / len(query_words)
            if match_ratio >= 0.5:
                return 1.0 + (match_ratio * 0.5)  # 1.0 to 1.5x boost
        
        return 1.0  # No boost
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search using Reciprocal Rank Fusion with enhanced phrase matching.
        
        Improvements:
        - Phrase matching score boost
        - Better handling of multi-word queries
        - Exact phrase detection
        - Important noun requirement for furniture queries
        """
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
            
            content = result.get('content', {})
            title = content.get('title', '').lower()
            description = content.get('description', '').lower()
            
            # Calculate phrase matching boost
            phrase_boost = self._calculate_phrase_score(query, title, description)
            
            # Legacy title boost (kept for compatibility)
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            legacy_title_boost = 1.0 + (title_match_count * 0.5)
            
            # Use maximum of phrase boost and legacy boost
            final_boost = max(phrase_boost, legacy_title_boost)
            
            combined_scores[doc_id] = {
                'score': self.alpha * rrf_score * final_boost,
                'result': result,
                'bm25_rank': rank,
                'vector_rank': None,
                'phrase_boost': phrase_boost,
                'title_boost': final_boost
            }
        
        # Vector scores
        for rank, result in enumerate(vector_results, start=1):
            doc_id = result['id']
            rrf_score = 1.0 / (60 + rank)
            
            content = result.get('content', {})
            title = content.get('title', '').lower()
            description = content.get('description', '').lower()
            
            # Calculate phrase matching boost
            phrase_boost = self._calculate_phrase_score(query, title, description)
            
            # Legacy title boost
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            legacy_title_boost = 1.0 + (title_match_count * 0.5)
            
            final_boost = max(phrase_boost, legacy_title_boost)
            
            if doc_id in combined_scores:
                combined_scores[doc_id]['score'] += (1 - self.alpha) * rrf_score * final_boost
                combined_scores[doc_id]['vector_rank'] = rank
                combined_scores[doc_id]['phrase_boost'] = max(
                    combined_scores[doc_id].get('phrase_boost', 1.0),
                    phrase_boost
                )
                combined_scores[doc_id]['title_boost'] = max(
                    combined_scores[doc_id]['title_boost'],
                    final_boost
                )
            else:
                combined_scores[doc_id] = {
                    'score': (1 - self.alpha) * rrf_score * final_boost,
                    'result': result,
                    'bm25_rank': None,
                    'vector_rank': rank,
                    'phrase_boost': phrase_boost,
                    'title_boost': final_boost
                }
        
        # Sort and apply strict filters/boosts
        sorted_candidates = sorted(combined_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        final_results = []
        
        for doc_id, data in sorted_candidates:
            title = data['result'].get('content', {}).get('title', '').lower()
            
            # Apply noun matching filter (only for furniture queries with nouns)
            if unique_base_nouns:
                matched_count = 0
                for base in unique_base_nouns:
                    if base in title or (base + 's') in title:
                        matched_count += 1
                
                match_ratio = matched_count / len(unique_base_nouns)
                
                # Boost products with all nouns matched
                if match_ratio >= 1.0:
                    data['score'] *= 2.0  # Full match - strong boost
                elif match_ratio >= 0.5:
                    data['score'] *= 1.5  # Partial match - medium boost
                elif match_ratio > 0:
                    data['score'] *= 1.2  # At least one noun - small boost
                else:
                    # No noun match - reduce score but don't filter out completely
                    data['score'] *= 0.3  # Low score but still included
            
            final_results.append({
                'id': doc_id,
                'score': data['score'],
                'content': data['result']['content'],
                'bm25_rank': data['bm25_rank'],
                'vector_rank': data['vector_rank'],
                'phrase_boost': data.get('phrase_boost', 1.0)
            })
            
            if len(final_results) >= limit + 5:  # Get a few extra for final re-sort
                break
        
        # Final re-sort after boosted scores
        final_results.sort(key=lambda x: x['score'], reverse=True)
        return final_results[:limit]
