"""
Hybrid Search - Combines BM25 and Vector Search

Uses Reciprocal Rank Fusion (RRF) to merge results with enhanced phrase matching.
Enhanced with smarter category detection and fallback strategies.
"""

from typing import List, Dict, Any, Optional, Tuple
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
        'drawer', 'drawers', 'ottoman', 'ottomans', 'rack', 'racks', 'stand', 'stands',
        'recliner', 'recliners', 'armchair', 'armchairs', 'lounge', 'lounges'
    }
    
    # Category mapping for filtering - expanded with related terms and Shopify categories
    CATEGORY_KEYWORDS = {
        'chair': ['chair', 'chairs', 'seating', 'seat', 'gaming chair', 'office chair', 'desk chair'],
        'table': ['table', 'tables', 'console table', 'coffee table', 'dining table', 'side table'],
        'desk': ['desk', 'desks', 'workstation', 'work station', 'computer desk', 'office desk', 'writing desk'],
        'sofa': ['sofa', 'sofas', 'couch', 'couches', 'settee', 'loveseat', 'lounge', 'lounger', 
                 'sectional', 'chaise', 'reception sofa', 'seater sofa', '2 seater', '3 seater', 'triple sofa'],
        'bed': ['bed', 'beds', 'mattress', 'mattresses', 'bedframe', 'bed frame', 'headboard', 'bunk'],
        'shelf': ['shelf', 'shelves', 'bookcase', 'bookcases', 'shelving', 'bookshelf', 'display unit'],
        'storage': ['storage', 'locker', 'lockers', 'cabinet', 'cabinets', 'wardrobe', 'wardrobes', 'drawer', 'chest', 'organizer'],
        'stool': ['stool', 'stools', 'ottoman', 'ottomans', 'bar stool', 'footstool', 'counter stool'],
        'recliner': ['recliner', 'recliners', 'reclining', 'lounge chair', 'lounger', 'massage chair'],
        'armchair': ['armchair', 'armchairs', 'arm chair'],
        # Common Shopify categories
        'lighting': ['lamp', 'lamps', 'light', 'lights', 'lighting', 'chandelier', 'pendant', 'sconce'],
        'outdoor': ['outdoor', 'patio', 'garden', 'deck', 'balcony', 'exterior'],
        'rug': ['rug', 'rugs', 'carpet', 'carpets', 'mat', 'mats', 'runner'],
        'mirror': ['mirror', 'mirrors', 'vanity'],
        'decor': ['decor', 'decoration', 'decorative', 'art', 'vase', 'ornament', 'wall art'],
    }
    
    # Category aliases - maps related categories together (but NOT the reverse)
    CATEGORY_ALIASES = {
        'sofa': ['lounge', 'settee'],  # sofa search also matches these - NOT chairs/armchairs
        'chair': ['stool', 'seating'],
        'recliner': ['lounge chair', 'lounger'],
        'table': ['desk'],
        'desk': ['table'],
        'storage': ['shelf', 'cabinet'],
        'bed': ['mattress'],
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
        'living': ['sofa', 'couch', 'coffee', 'entertainment', 'lounge', 'recliner', 'armchair'],
        'living room': ['sofa', 'couch', 'lounge', 'recliner', 'armchair', 'ottoman', 'coffee table'],
    }
    
    # Query expansion - map common synonyms to search terms
    QUERY_SYNONYMS = {
        'cheap': ['budget', 'affordable', 'value', 'low price'],
        'expensive': ['premium', 'luxury', 'high-end', 'designer'],
        'couch': ['sofa', 'settee', 'lounge'],
        'cupboard': ['cabinet', 'storage', 'wardrobe'],
        'wardrobe': ['closet', 'armoire', 'clothes storage'],
        'nightstand': ['bedside table', 'night table', 'end table'],
        'dresser': ['chest of drawers', 'bureau', 'drawers'],
        'bookshelf': ['bookcase', 'shelving', 'book storage'],
        'lamp': ['light', 'lighting', 'table lamp'],
        'rug': ['carpet', 'floor mat', 'area rug'],
        'small': ['compact', 'mini', 'little'],
        'big': ['large', 'oversized', 'spacious'],
        'modern': ['contemporary', 'minimalist', 'sleek'],
        'rustic': ['farmhouse', 'country', 'vintage'],
        'comfy': ['comfortable', 'cozy', 'plush'],
    }
    
    def __init__(self, bm25_index: BM25Index, vector_index: VectorIndex, alpha: float = 0.5):
        self.bm25_index = bm25_index
        self.vector_index = vector_index
        self.alpha = alpha
        self._query_cache = {}  # Cache for query expansion
        self._cache_max_size = 200
    
    def _expand_query(self, query: str) -> str:
        """
        Expand query with synonyms for better recall.
        
        Args:
            query: Original search query
            
        Returns:
            Expanded query with synonyms added
        """
        # Check cache first
        if query in self._query_cache:
            return self._query_cache[query]
        
        query_lower = query.lower()
        expanded_terms = [query_lower]
        
        # Add synonyms for any matching words
        for word, synonyms in self.QUERY_SYNONYMS.items():
            if word in query_lower:
                # Add first 2 synonyms to avoid query explosion
                expanded_terms.extend(synonyms[:2])
        
        # Build expanded query (original + key synonyms)
        expanded = ' '.join(expanded_terms)
        
        # Cache the result
        if len(self._query_cache) >= self._cache_max_size:
            # Clear oldest entry
            first_key = next(iter(self._query_cache))
            del self._query_cache[first_key]
        self._query_cache[query] = expanded
        
        if expanded != query_lower:
            print(f"[HYBRID_SEARCH] Query expanded: '{query}' -> '{expanded[:80]}...'")
        
        return expanded
    
    def _extract_primary_category(self, query: str) -> Tuple[Optional[str], List[str]]:
        """
        Extract the primary product category and related categories from query.
        
        Returns:
            Tuple of (primary_category, list of all matching keywords)
        """
        query_lower = query.lower()
        
        # Check for category keywords in order of specificity
        priority_order = ['lighting', 'rug', 'mirror', 'decor', 'sofa', 'recliner', 'chair', 'bed', 'desk', 'table', 'shelf', 'stool', 'storage', 'outdoor']
        
        for category in priority_order:
            if category in self.CATEGORY_KEYWORDS:
                keywords = self.CATEGORY_KEYWORDS[category]
                for keyword in keywords:
                    if keyword in query_lower:
                        # Get all related keywords including aliases
                        all_keywords = list(keywords)
                        if category in self.CATEGORY_ALIASES:
                            for alias in self.CATEGORY_ALIASES[category]:
                                if alias in self.CATEGORY_KEYWORDS:
                                    all_keywords.extend(self.CATEGORY_KEYWORDS[alias])
                        
                        print(f"[HYBRID_SEARCH] Extracted category: {category} (matched '{keyword}' in query '{query}')")
                        print(f"[HYBRID_SEARCH] All matching keywords: {all_keywords[:10]}...")
                        return category, list(set(all_keywords))
        
        print(f"[HYBRID_SEARCH] No category extracted from query: {query}")
        return None, []
    
    def _check_category_match(self, text: str, category_keywords: List[str], primary_category: str = None) -> Tuple[bool, float]:
        """
        Check if text matches any category keywords.
        
        Returns:
            Tuple of (has_match, match_score)
            - has_match: True if any keyword found
            - match_score: 0.0-1.0 indicating strength of match
        """
        text_lower = text.lower()
        matches = 0
        primary_match = False
        
        for keyword in category_keywords:
            if keyword in text_lower:
                matches += 1
                # Exact word match is stronger
                if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                    matches += 1
                    # If the primary category word itself matches (e.g., "sofa" in "reception sofa")
                    if primary_category and keyword == primary_category:
                        primary_match = True
                        matches += 3  # Strong boost for exact primary category match
        
        if matches > 0:
            # Normalize score (cap at 1.0)
            base_score = min(matches / 4.0, 1.0)
            # Extra boost if primary category matches
            if primary_match:
                base_score = min(base_score * 1.5, 1.0)
            return True, base_score
        
        return False, 0.0
    
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
        Optimized for large catalogs (2000+ products).
        
        Improvements:
        - Query expansion with synonyms for better recall
        - Phrase matching score boost (10x for exact match)
        - Semantic similarity threshold filtering
        - Category-based filtering with smart fallback
        - Negative keyword penalties
        - Intent-based boosting
        - Better handling of multi-word queries
        - Important noun requirement for furniture queries
        """
        query_lower = query.lower()
        
        # Expand query with synonyms for better recall
        expanded_query = self._expand_query(query_lower)
        
        # Extract primary category and all related keywords
        primary_category, category_keywords = self._extract_primary_category(query_lower)
        
        # Get more results for filtering (increased for large catalogs)
        candidate_limit = min(limit * 10, 100)  # Get 10x but cap at 100
        
        # Use expanded query for BM25 (keyword-based), original for vector (semantic)
        bm25_results = self.bm25_index.search(expanded_query, limit=candidate_limit)
        vector_results = self.vector_index.search(query_lower, limit=candidate_limit)
        
        print(f"[HYBRID_SEARCH] BM25 returned {len(bm25_results)} results, Vector returned {len(vector_results)} results")
        
        # Semantic similarity threshold (ChromaDB uses distance, lower is better)
        # For cosine distance: 0 = identical, 2 = opposite
        # Relaxed threshold for large catalogs with diverse products
        SEMANTIC_THRESHOLD = 0.85
        
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
        
        # Sort and apply filters/boosts with smart category matching
        sorted_candidates = sorted(combined_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # FIRST PASS: Strict category filtering
        category_matched = []
        category_unmatched = []
        
        print(f"[HYBRID_SEARCH] Primary category: {primary_category}")
        print(f"[HYBRID_SEARCH] Category keywords: {category_keywords[:5]}..." if category_keywords else "[HYBRID_SEARCH] No category keywords")
        print(f"[HYBRID_SEARCH] Processing {len(sorted_candidates)} candidates")
        
        filtered_count = 0
        for doc_id, data in sorted_candidates:
            title = data['result'].get('content', {}).get('title', '').lower()
            description = data['result'].get('content', {}).get('description', '').lower()
            tags = str(data['result'].get('content', {}).get('tags', '')).lower()
            product_type = str(data['result'].get('content', {}).get('type', '')).lower()
            
            # Combine all text fields for matching
            text = f"{title} {description} {tags} {product_type}"
            
            # Check category match using expanded keywords
            if primary_category and category_keywords:
                # Pass primary_category for stronger matching
                has_match, match_score = self._check_category_match(text, category_keywords, primary_category)
                
                # STRICT CHECK: Does the title contain the primary category word?
                title_has_primary = primary_category in title
                
                if has_match:
                    # Extra boost if primary category is directly in the title
                    if title_has_primary:
                        data['score'] *= (1.5 + match_score)  # Stronger boost
                        data['primary_title_match'] = True
                    else:
                        data['score'] *= (1.0 + match_score * 0.5)  # Weaker boost for non-title matches
                        data['primary_title_match'] = False
                    data['category_match'] = True
                    category_matched.append((doc_id, data))
                else:
                    filtered_count += 1
                    if filtered_count <= 3:
                        print(f"[HYBRID_SEARCH] ❌ FILTERED: '{title[:50]}' (no match for category '{primary_category}')")
                    data['category_match'] = False
                    category_unmatched.append((doc_id, data))
            else:
                # No category filter - include all
                data['category_match'] = True
                category_matched.append((doc_id, data))
        
        # Sort category_matched by score (so title matches come first)
        category_matched.sort(key=lambda x: x[1]['score'], reverse=True)
        
        # FALLBACK: If strict filtering yields too few results, include some unmatched
        MIN_RESULTS = 3
        if len(category_matched) < MIN_RESULTS and category_unmatched:
            print(f"[HYBRID_SEARCH] ⚠️ Only {len(category_matched)} category matches, adding fallback results")
            
            # Sort unmatched by score and add top ones with penalty
            category_unmatched.sort(key=lambda x: x[1]['score'], reverse=True)
            for doc_id, data in category_unmatched[:MIN_RESULTS - len(category_matched)]:
                data['score'] *= 0.3  # Heavier penalty for non-matching category
                data['is_fallback'] = True
                category_matched.append((doc_id, data))
                title = data['result'].get('content', {}).get('title', '')
                print(f"[HYBRID_SEARCH] ➕ FALLBACK: '{title[:50]}'")
        
        # Apply noun matching and build final results
        final_results = []
        
        for doc_id, data in category_matched:
            title = data['result'].get('content', {}).get('title', '').lower()
            
            # Apply noun matching filter (only for furniture queries with nouns)
            if unique_base_nouns:
                matched_count = 0
                for base in unique_base_nouns:
                    if base in title or (base + 's') in title:
                        matched_count += 1
                
                match_ratio = matched_count / len(unique_base_nouns) if unique_base_nouns else 0
                
                # Boost products with all nouns matched
                if match_ratio >= 1.0:
                    data['score'] *= 2.0  # Full match - strong boost
                elif match_ratio >= 0.5:
                    data['score'] *= 1.5  # Partial match - medium boost
                elif match_ratio > 0:
                    data['score'] *= 1.2  # At least one noun - small boost
                # Don't penalize if category already matched
            
            final_results.append({
                'id': doc_id,
                'score': data['score'],
                'content': data['result']['content'],
                'bm25_rank': data['bm25_rank'],
                'vector_rank': data['vector_rank'],
                'semantic_distance': data.get('semantic_distance'),
                'phrase_boost': data.get('phrase_boost', 1.0),
                'negative_penalty': data.get('negative_penalty', 1.0),
                'intent_boost': data.get('intent_boost', 1.0),
                'category_match': data.get('category_match', False),
                'is_fallback': data.get('is_fallback', False)
            })
            
            if len(final_results) >= limit + 5:  # Get a few extra for final re-sort
                break
        
        # Final re-sort after all boosts applied
        final_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Log final results
        print(f"[HYBRID_SEARCH] ✅ Returning {min(len(final_results), limit)} results")
        if final_results:
            for i, r in enumerate(final_results[:3]):
                title = r['content'].get('title', 'Unknown')[:40]
                print(f"[HYBRID_SEARCH]   {i+1}. {title}... (score: {r['score']:.4f}, cat_match: {r.get('category_match', '?')})")
        
        return final_results[:limit]
