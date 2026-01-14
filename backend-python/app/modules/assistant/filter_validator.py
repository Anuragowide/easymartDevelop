"""
Filter validation module for enforcing multi-filter requirements and detecting contradictions.
"""
from typing import Dict, Any, Optional, Tuple, List
import re


class FilterValidator:
    """Validates filter combinations and enforces minimum filter requirements."""
    
    # Filter weight mappings - determines how much each filter contributes to total
    FILTER_WEIGHTS = {
        'category': 1.0,
        'subcategory': 1.0,  # MMA, Boxing, Dumbbells, etc.
        'product_type': 1.0,  # gloves, bag, bench, etc.
        'color': 1.0,
        'material': 1.0,
        'style': 1.0,
        'room_type': 0.8,
        'descriptor': 0.8,  # horizontal, vertical, adjustable, etc.
        'price_max': 0.5,
        'age_group': 0.5,
    }
    
    # Subjective terms have lower weight (semantic matching only)
    SUBJECTIVE_TERM_WEIGHT = 0.3
    
    # Minimum total weight required to proceed with search
    # Set to 1.0 - a single clear product type is enough
    MIN_FILTER_WEIGHT = 1.0
    
    # Incompatible filter pairs that create contradictions
    INCOMPATIBLE_PAIRS = [
        ('cheap', 'luxury'),
        ('cheap', 'expensive'),
        ('cheap', 'premium'),
        ('affordable', 'luxury'),
        ('budget', 'premium'),
        ('small', 'large'),
        ('compact', 'spacious'),
        ('minimalist', 'ornate'),
        ('simple', 'ornate'),
        ('modern', 'classic'),
        ('modern', 'vintage'),
        ('contemporary', 'traditional'),
    ]
    
    # Bypass phrases that allow user to skip clarification
    BYPASS_PHRASES = [
        'show me anything',
        'just search',
        'you choose',
        'surprise me',
        'whatever',
        "don't care",
        'any will do',
        'any is fine',
        'anything',
        'just show me',
    ]
    
    def __init__(self):
        """Initialize the filter validator."""
        pass
    
    def validate_filter_count(
        self, 
        entities: Dict[str, Any],
        query: str = ""
    ) -> Tuple[bool, float, str]:
        """
        Validate if the filter combination meets minimum requirements.
        
        Args:
            entities: Extracted entities dictionary (category, color, material, etc.)
            query: Original user query for detecting subjective terms
            
        Returns:
            Tuple of (is_valid, total_weight, message)
            - is_valid: True if filters meet minimum requirements
            - total_weight: Calculated weight score
            - message: Helpful message indicating what's needed
        """
        total_weight = 0.0
        present_filters = []
        
        # Special case: Check for CLEAR product queries that don't need clarification
        # Examples: "mma gloves", "boxing bag", "dog kennel", "electric scooter"
        query_lower = query.lower() if query else ""
        
        # Product category keywords (count as 1.0 weight each)
        category_keywords = [
            # Sports & Fitness - Cardio
            'fitness', 'gym', 'exercise', 'workout', 'training', 'cardio',
            'treadmill', 'treadmills', 'exercise bike', 'rowing', 'rower', 'elliptical',
            # Sports & Fitness - Weights
            'weightlifting', 'weight lifting', 'weights', 'dumbbell', 'dumbbells',
            'kettlebell', 'kettlebells', 'barbell', 'barbells', 'weight plates', 'olympic',
            # Sports & Fitness - Boxing/MMA
            'mma', 'boxing', 'muay thai', 'kickboxing', 'martial arts', 'karate',
            'taekwondo', 'judo', 'jiu jitsu', 'bjj', 'sparring', 'punching',
            # Sports & Fitness - General
            'trampoline', 'air track', 'gymnastics', 'yoga', 'pilates',
            'massage', 'relaxation', 'foam roller', 'recovery', 'stretching',
            'rugby', 'basketball', 'sports',
            # Pet Products
            'dog', 'cat', 'pet', 'puppy', 'kitten', 'bird', 'aquarium', 'fish tank',
            # Electric Scooters  
            'scooter', 'e-scooter', 'escooter', 'electric scooter',
            # Furniture
            'office', 'gaming', 'ergonomic', 'furniture', 'desk', 'chair', 'table',
            'sofa', 'bed', 'mattress', 'cabinet', 'shelf', 'bookcase'
        ]
        
        # Product type keywords (count as 1.0 weight each)
        product_type_keywords = [
            # Boxing/MMA
            'gloves', 'bag', 'bags', 'pads', 'shield', 'shields', 'ring', 'rings',
            'uniform', 'belt', 'helmet', 'guard', 'guards', 'wraps', 'protector',
            # Gym Equipment
            'bench', 'benches', 'rack', 'racks', 'mat', 'mats', 'plates', 'sets',
            'machine', 'machines', 'equipment', 'gear', 'roller', 'ball', 'bands',
            # Pet Products
            'kennel', 'kennels', 'cage', 'cages', 'crate', 'tree', 'tower',
            'bed', 'beds', 'bowl', 'bowls', 'collar', 'leash', 'toy', 'toys',
            'pump', 'filter', 'litter', 'carrier',
            # Electric Scooters
            'scooter', 'scooters', 'wheel', 'wheels', 'battery',
            # Furniture
            'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas',
            'cabinet', 'cabinets', 'shelf', 'shelves', 'stool', 'stools',
            'ottoman', 'recliner', 'bookcase'
        ]
        
        # Check for category keywords
        has_category = any(keyword in query_lower for keyword in category_keywords)
        if has_category:
            total_weight += 1.0
            present_filters.append('category')
        
        # Check for product type keywords
        has_product_type = any(keyword in query_lower for keyword in product_type_keywords)
        if has_product_type:
            total_weight += 1.0
            present_filters.append('product_type')
        
        # Calculate weight from structured entities
        for filter_name, weight in self.FILTER_WEIGHTS.items():
            if entities.get(filter_name):
                total_weight += weight
                present_filters.append(filter_name)
        
        # Add weight for subjective terms in query
        subjective_count = self._count_subjective_terms(query)
        total_weight += subjective_count * self.SUBJECTIVE_TERM_WEIGHT
        
        # Check if minimum threshold met
        is_valid = total_weight >= self.MIN_FILTER_WEIGHT
        
        # Generate helpful message
        if is_valid:
            message = f"Sufficient filters provided (weight: {total_weight:.1f})"
        else:
            needed_weight = self.MIN_FILTER_WEIGHT - total_weight
            message = self._generate_filter_suggestion(present_filters, needed_weight)
        
        return is_valid, total_weight, message
    
    def _count_subjective_terms(self, query: str) -> int:
        """Count subjective terms in query (cheap, expensive, small, large, etc.)."""
        if not query:
            return 0
        
        query_lower = query.lower()
        subjective_terms = [
            'cheap', 'affordable', 'budget', 'expensive', 'premium', 'luxury',
            'small', 'compact', 'large', 'spacious', 'tiny', 'huge',
            'cozy', 'comfortable', 'sturdy', 'elegant', 'stylish',
            'horizontal', 'vertical', 'adjustable', 'stackable', 'foldable',
            # Sports/fitness specific
            'leather', 'padded', 'heavy', 'light', 'professional', 'training', 'sparring'
        ]
        
        count = 0
        for term in subjective_terms:
            if re.search(r'\b' + term + r'\b', query_lower):
                count += 1
        
        return min(count, 3)  # Cap at 3 to avoid over-counting
    
    def _generate_filter_suggestion(
        self, 
        present_filters: List[str],
        needed_weight: float
    ) -> str:
        """Generate a helpful suggestion for what filters are needed."""
        if not present_filters:
            return "Is there anything specific you have in mind? (For example: size, color, material, price range, or any other preference)"
        
        # Determine what type of filter is present
        has_category = 'category' in present_filters
        has_attribute = any(f in present_filters for f in ['color', 'material', 'style', 'descriptor'])
        has_context = any(f in present_filters for f in ['room_type', 'age_group'])
        has_price = 'price_max' in present_filters
        
        suggestions = []
        
        if has_category and not has_attribute:
            suggestions.append("color, material, or style")
        elif has_attribute and not has_category:
            suggestions.append("furniture type (chair, table, desk, etc.)")
        
        if not has_context:
            suggestions.append("room or purpose (office, bedroom, for kids, gym, school, etc.)")
        
        if not has_price and needed_weight >= 0.5:
            suggestions.append("price range")
        
        if suggestions:
            suggestion_text = ", ".join(suggestions[:2])  # Limit to 2 suggestions
            return f"Is there anything specific you have in mind? (For example: {suggestion_text}, or any other preference)"
        
        return "Can you please tell me more about what you want?"
    
    def detect_contradictions(
        self, 
        entities: Dict[str, Any],
        query: str = ""
    ) -> Optional[Tuple[str, str, str]]:
        """
        Detect contradictory filter combinations.
        
        Args:
            entities: Extracted entities dictionary
            query: Original user query
            
        Returns:
            Tuple of (term1, term2, clarification_message) if contradiction found, else None
        """
        # Combine all filter values and query into searchable text
        search_text = query.lower()
        for key, value in entities.items():
            if value and isinstance(value, str):
                search_text += f" {value.lower()}"
        
        # Check for incompatible pairs
        for term1, term2 in self.INCOMPATIBLE_PAIRS:
            has_term1 = re.search(r'\b' + term1 + r'\b', search_text)
            has_term2 = re.search(r'\b' + term2 + r'\b', search_text)
            
            if has_term1 and has_term2:
                message = self._generate_contradiction_message(term1, term2)
                return (term1, term2, message)
        
        return None
    
    def _generate_contradiction_message(self, term1: str, term2: str) -> str:
        """Generate a clarification message for contradictory terms."""
        # Handle price-related contradictions
        if term1 in ['cheap', 'affordable', 'budget'] and term2 in ['luxury', 'expensive', 'premium']:
            return f"I noticed you mentioned both '{term1}' and '{term2}'. Would you prefer: (A) Affordable options, (B) Premium options, or (C) Mid-range quality furniture?"
        
        # Handle size contradictions
        if term1 in ['small', 'compact'] and term2 in ['large', 'spacious']:
            return f"I see both '{term1}' and '{term2}' mentioned. Which size do you prefer: (A) Compact/small, or (B) Large/spacious?"
        
        # Handle style contradictions
        if (term1 in ['modern', 'contemporary', 'minimalist'] and 
            term2 in ['classic', 'traditional', 'vintage', 'ornate']):
            return f"You mentioned both '{term1}' and '{term2}' styles. Which direction would you like: (A) Modern/contemporary, or (B) Classic/traditional?"
        
        # Generic contradiction message
        return f"I noticed both '{term1}' and '{term2}' in your request. Could you clarify which one you prefer?"
    
    def is_bypass_phrase(self, message: str) -> bool:
        """
        Check if the user message contains a bypass phrase.
        
        Args:
            message: User's message
            
        Returns:
            True if message contains bypass phrase
        """
        message_lower = message.lower().strip()
        
        # Check exact matches
        for phrase in self.BYPASS_PHRASES:
            if phrase in message_lower:
                return True
        
        # Check very short affirmative responses during clarification
        short_responses = ['ok', 'okay', 'yes', 'sure', 'fine', 'go ahead']
        if message_lower in short_responses:
            return True
        
        return False
    
    def get_filter_summary(self, entities: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of active filters.
        
        Args:
            entities: Extracted entities dictionary
            
        Returns:
            String summary of filters
        """
        filters = []
        
        if entities.get('category'):
            filters.append(entities['category'])
        
        if entities.get('color'):
            filters.append(f"{entities['color']} color")
        
        if entities.get('material'):
            filters.append(f"{entities['material']} material")
        
        if entities.get('style'):
            filters.append(f"{entities['style']} style")
        
        if entities.get('room_type'):
            filters.append(f"for {entities['room_type']}")
        
        if entities.get('age_group'):
            filters.append(f"for {entities['age_group']}")
        
        if entities.get('price_max'):
            filters.append(f"under ${entities['price_max']}")
        
        if not filters:
            return "no specific filters"
        
        return ", ".join(filters)
