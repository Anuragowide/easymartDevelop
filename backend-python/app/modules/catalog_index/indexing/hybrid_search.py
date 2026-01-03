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
    
    # Category mapping for strict filtering
    CATEGORY_KEYWORDS = {
        'chair': ['chair', 'chairs', 'seating', 'seat'],
        'table': ['table', 'tables', 'console table', 'coffee table', 'dining table', 'side table'],
        'desk': ['desk', 'desks', 'workstation', 'work station'],
        'sofa': ['sofa', 'sofas', 'couch', 'couches', 'settee', 'loveseat'],
        'bed': ['bed', 'beds', 'mattress', 'mattresses'],
        'shelf': ['shelf', 'shelves', 'bookcase', 'bookcases', 'shelving'],
        'storage': ['storage', 'locker', 'lockers', 'cabinet', 'cabinets', 'wardrobe', 'wardrobes'],
        'stool': ['stool', 'stools', 'ottoman', 'ottomans', 'bar stool']
    }
    
    # Incompatible keyword pairs - if query has key, penalize results with values
    NEGATIVE_KEYWORDS = {
        'gaming': ['kids', 'kid', 'children', 'child', 'baby', 'toddler', 'toy', 'playground', 'plastic'],
        'office': ['kids', 'kid', 'children', 'child', 'baby', 'toddler', 'toy', 'playground'],
        'professional': ['kids', 'kid', 'children', 'child', 'baby', 'toy', 'plastic'],
        'executive': ['kids', 'kid', 'children', 'child', 'baby', 'toy', 'plastic'],
        'ergonomic': ['kids', 'kid', 'children', 'toy', 'plastic'],
        'adult': ['kids', 'kid', 'children', 'child', 'baby', 'toddler', 'toy'],
        'premium': ['cheap', 'budget', 'plastic', 'toy'],
        'luxury': ['cheap', 'budget', 'plastic', 'toy'],
        'leather': ['plastic', 'pvc'],
        'metal': ['plastic', 'cardboard'],
        'wood': ['plastic', 'cardboard'],
        'kids': ['office', 'executive', 'professional', 'gaming', 'adult'],
        'children': ['office', 'executive', 'professional', 'gaming', 'adult'],
    }
    
    # Intent-related keywords for boosting
    INTENT_KEYWORDS = {
        'gaming': ['rgb', 'racing', 'ergonomic', 'reclining', 'adjustable', 'swivel', 'lumbar'],
        'office': ['ergonomic', 'executive', 'professional', 'swivel', 'adjustable', 'mesh', 'lumbar'],
        'kids': ['child', 'children', 'youth', 'junior', 'study', 'colorful', 'small'],
        'outdoor': ['weather', 'waterproof', 'patio', 'garden', 'resistant'],
        'bedroom': ['bed', 'nightstand', 'dresser', 'wardrobe', 'sleeping'],
        'living': ['sofa', 'couch', 'coffee', 'entertainment', 'lounge'],
    }
    
    def __init__(self, bm25_index: BM25Index, vector_index: VectorIndex, alpha: float = 0.5):
        self.bm25_index = bm25_index
        self.vector_index = vector_index
        self.alpha = alpha
    
    def _extract_primary_category(self, query: str) -> str:
        """Extract the primary product category from query."""
        query_lower = query.lower()
        
        # Check for category keywords in order of specificity
        # Check most specific first (sofa before 'so', desk before table)
        priority_order = ['sofa', 'chair', 'bed', 'desk', 'table', 'shelf', 'stool', 'storage']
        
        for category in priority_order:
            if category in self.CATEGORY_KEYWORDS:
                keywords = self.CATEGORY_KEYWORDS[category]
                for keyword in keywords:
                    if keyword in query_lower:
                        print(f"[HYBRID_SEARCH] Extracted category: {category} (matched '{keyword}' in query '{query}')")
                        return category
        
        print(f"[HYBRID_SEARCH] No category extracted from query: {query}")
        return None
    
    def _extract_intent_keywords(self, query: str) -> List[str]:
        """Extract intent keywords from query (gaming, office, kids, etc.)."""
        query_lower = query.lower()
        found_intents = []
        
        for intent in self.INTENT_KEYWORDS.keys():
            if intent in query_lower:
                found_intents.append(intent)
        
        return found_intents
    
    def _calculate_negative_keyword_penalty(self, query: str, title: str, description: str) -> float:
        """Calculate penalty for incompatible keywords.
        
        Returns a multiplier: 1.0 (no penalty) to 0.1 (heavy penalty)
        """
        query_lower = query.lower()
        text_lower = (title + ' ' + description).lower()
        
        penalty = 1.0
        
        for query_keyword, negative_keywords in self.NEGATIVE_KEYWORDS.items():
            if query_keyword in query_lower:
                for negative_keyword in negative_keywords:
                    if negative_keyword in text_lower:
                        # Heavy penalty for incompatible context
                        penalty *= 0.1
                        break  # One penalty per query keyword is enough
        
        return penalty
    
    def _calculate_intent_boost(self, query: str, title: str, description: str) -> float:
        """Boost results that match query intent.
        
        Returns a multiplier: 1.0 (no boost) to 2.0 (strong boost)
        """
        intent_keywords = self._extract_intent_keywords(query)
        
        if not intent_keywords:
            return 1.0  # No intent detected
        
        text_lower = (title + ' ' + description).lower()
        boost = 1.0
        
        for intent in intent_keywords:
            related_keywords = self.INTENT_KEYWORDS.get(intent, [])
            matched_count = sum(1 for kw in related_keywords if kw in text_lower)
            
            if matched_count > 0:
                # Boost based on how many related keywords matched
                boost += 0.3 * min(matched_count, 3)  # Cap at 3 keywords
        
        return min(boost, 2.0)  # Cap at 2.0x
    
    def _calculate_phrase_score(self, query: str, title: str, description: str) -> float:
        """
        Calculate phrase matching score.
        
        Boosts results where:
        - Exact phrase appears in title (highest boost - 10x)
        - All query terms appear in title (high boost - 5x)
        - Exact phrase appears in description (medium boost - 3x)
        - All query terms appear in description (low boost - 2x)
        """
        query_lower = query.lower().strip()
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Exact phrase in title = 10x boost (increased from 5x)
        if query_lower in title_lower:
            return 10.0
        
        # All words in title = 5x boost (increased from 3x)
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        title_words = set(re.findall(r'\b\w+\b', title_lower))
        if query_words.issubset(title_words):
            return 5.0
        
        # Exact phrase in description = 3x boost (increased from 2x)
        if query_lower in desc_lower:
            return 3.0
        
        # All words in description = 2x boost (increased from 1.5x)
        desc_words = set(re.findall(r'\b\w+\b', desc_lower))
        if query_words.issubset(desc_words):
            return 2.0
        
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
        - Phrase matching score boost (10x for exact match)
        - Semantic similarity threshold filtering
        - Category-based filtering
        - Negative keyword penalties
        - Intent-based boosting
        - Better handling of multi-word queries
        - Exact phrase detection
        - Important noun requirement for furniture queries
        """
        query_lower = query.lower()
        
        # Extract primary category and intent from query
        primary_category = self._extract_primary_category(query_lower)
        
        # Get more results for filtering
        bm25_results = self.bm25_index.search(query_lower, limit=limit * 3)
        vector_results = self.vector_index.search(query_lower, limit=limit * 3)
        
        # Semantic similarity threshold (ChromaDB uses distance, lower is better)
        # For cosine distance: 0 = identical, 2 = opposite
        # We want distance < 0.8 (similarity > 0.6)
        SEMANTIC_THRESHOLD = 0.8
        
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
        
        # BM25 scores with category and negative keyword filtering
        for rank, result in enumerate(bm25_results, start=1):
            doc_id = result['id']
            rrf_score = 1.0 / (60 + rank)
            
            content = result.get('content', {})
            title = content.get('title', '').lower()
            description = content.get('description', '').lower()
            
            # Calculate phrase matching boost
            phrase_boost = self._calculate_phrase_score(query, title, description)
            
            # Calculate negative keyword penalty
            negative_penalty = self._calculate_negative_keyword_penalty(query, title, description)
            
            # Calculate intent boost
            intent_boost = self._calculate_intent_boost(query, title, description)
            
            # Legacy title boost (kept for compatibility)
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            legacy_title_boost = 1.0 + (title_match_count * 0.5)
            
            # Use maximum of phrase boost and legacy boost, apply penalties and boosts
            final_boost = max(phrase_boost, legacy_title_boost) * intent_boost * negative_penalty
            
            combined_scores[doc_id] = {
                'score': self.alpha * rrf_score * final_boost,
                'result': result,
                'bm25_rank': rank,
                'vector_rank': None,
                'semantic_distance': None,
                'phrase_boost': phrase_boost,
                'title_boost': final_boost,
                'negative_penalty': negative_penalty,
                'intent_boost': intent_boost
            }
        
        # Vector scores with semantic threshold filtering
        for rank, result in enumerate(vector_results, start=1):
            doc_id = result['id']
            semantic_distance = result.get('score', 0.0)
            
            # Filter out results with low semantic similarity
            if semantic_distance > SEMANTIC_THRESHOLD:
                continue  # Skip semantically distant results
            
            rrf_score = 1.0 / (60 + rank)
            
            content = result.get('content', {})
            title = content.get('title', '').lower()
            description = content.get('description', '').lower()
            
            # Calculate phrase matching boost
            phrase_boost = self._calculate_phrase_score(query, title, description)
            
            # Calculate negative keyword penalty
            negative_penalty = self._calculate_negative_keyword_penalty(query, title, description)
            
            # Calculate intent boost
            intent_boost = self._calculate_intent_boost(query, title, description)
            
            # Legacy title boost
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            legacy_title_boost = 1.0 + (title_match_count * 0.5)
            
            final_boost = max(phrase_boost, legacy_title_boost) * intent_boost * negative_penalty
            
            if doc_id in combined_scores:
                combined_scores[doc_id]['score'] += (1 - self.alpha) * rrf_score * final_boost
                combined_scores[doc_id]['vector_rank'] = rank
                combined_scores[doc_id]['semantic_distance'] = semantic_distance
                combined_scores[doc_id]['phrase_boost'] = max(
                    combined_scores[doc_id].get('phrase_boost', 1.0),
                    phrase_boost
                )
                combined_scores[doc_id]['title_boost'] = max(
                    combined_scores[doc_id]['title_boost'],
                    final_boost
                )
                combined_scores[doc_id]['negative_penalty'] = min(
                    combined_scores[doc_id].get('negative_penalty', 1.0),
                    negative_penalty
                )
                combined_scores[doc_id]['intent_boost'] = max(
                    combined_scores[doc_id].get('intent_boost', 1.0),
                    intent_boost
                )
            else:
                combined_scores[doc_id] = {
                    'score': (1 - self.alpha) * rrf_score * final_boost,
                    'result': result,
                    'bm25_rank': None,
                    'vector_rank': rank,
                    'semantic_distance': semantic_distance,
                    'phrase_boost': phrase_boost,
                    'title_boost': final_boost,
                    'negative_penalty': negative_penalty,
                    'intent_boost': intent_boost
                }
        
        # Sort and apply strict filters/boosts
        sorted_candidates = sorted(combined_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        final_results = []
        
        print(f"[HYBRID_SEARCH] Primary category: {primary_category}")
        print(f"[HYBRID_SEARCH] Processing {len(sorted_candidates)} candidates")
        
        filtered_count = 0
        for doc_id, data in sorted_candidates:
            title = data['result'].get('content', {}).get('title', '').lower()
            description = data['result'].get('content', {}).get('description', '').lower()
            text = title + ' ' + description
            
            # STEP 1: Strict category filtering - EXCLUDE products that don't match
            if primary_category:
                category_keywords = self.CATEGORY_KEYWORDS.get(primary_category, [])
                has_category_match = any(kw in text for kw in category_keywords)
                
                if not has_category_match:
                    # Product doesn't match required category - SKIP IT ENTIRELY
                    filtered_count += 1
                    if filtered_count <= 3:  # Log first 3 filtered items
                        print(f"[HYBRID_SEARCH] ❌ FILTERED: '{title[:50]}' (no match for category '{primary_category}')")
                    continue  # Skip this product entirely
            
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
                'semantic_distance': data.get('semantic_distance'),
                'phrase_boost': data.get('phrase_boost', 1.0),
                'negative_penalty': data.get('negative_penalty', 1.0),
                'intent_boost': data.get('intent_boost', 1.0)
            })
            
            if len(final_results) >= limit + 5:  # Get a few extra for final re-sort
                break
        
        # Final re-sort after boosted scores
        final_results.sort(key=lambda x: x['score'], reverse=True)
        return final_results[:limit]
