"""
Category Intelligence Module

Provides intelligent category mapping based on the ACTUAL product catalog.
This grounds all LLM understanding in real inventory categories.
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

# =============================================================================
# ACTUAL CATALOG CATEGORIES (from your Shopify inventory)
# =============================================================================

ALL_CATEGORIES = [
    "Accessories", "Air Track Mat", "Aquarium", "Bar Stool", "Basketball",
    "Bathroom Furniture", "Bed", "Bench", "Bikes", "Bird Cages & Stands",
    "Body Protector", "Bookcase", "Boxing & Muay Thai", "CCTV Camera",
    "Cat Supplies", "Chairs", "Desks", "Desks Frame", "Dining Room Furniture",
    "Dog Supplies", "Dumbbells", "Electric Scooters", "Electric Scooters Accessories",
    "Exercise Bikes", "Filing Cabinets", "Fitness", "Fitness Accessories",
    "Flooring & Mats", "Focus Pads", "Functional Fitness", "General", "Gloves",
    "Golf", "Gym Bench", "Gym Sanitizer", "Home & Garden", "Home Furniture",
    "Kettlebells", "Kids Furniture", "Lectern", "Living Room Furniture",
    "Locker Stand", "Locker Top", "Lounge", "MMA", "Martial Arts", "Mattresses",
    "Mirror", "Monitor Arm", "Office Cupboards", "Office Shelving",
    "Other Pet Supplies", "Ottoman", "Outdoor Furniture", "Pedestals",
    "Pet Care Coops & Hutches", "Pet Care Farm Supplies", "Pet Carrier",
    "Pet Feeder", "Pet Fountain", "Pets", "Photography", "Power Point",
    "Projectors & Accessories", "Rabbit Cage", "Rashguard Shirts",
    "Reception Counters", "Recliners", "Rowing Machine", "Rugby", "Safety Lock",
    "Screens", "Shelves", "Snughooks", "Sofa", "Speakers", "Storage",
    "TV Acessories", "Table & Chair Set", "Table Components", "Tables",
    "Thai Pads", "Training Chairs", "Trampoline", "Treadmills", "Trolley",
    "Vertical Garden", "Weightlifting", "Whiteboard", "Whiteboards",
    "Workstation", "Workstation Component", "Yoga Mat", "lockers"
]

# =============================================================================
# CATEGORY GROUPS - Logical groupings of related categories
# =============================================================================

CATEGORY_GROUPS = {
    "pet": [
        "Dog Supplies", "Cat Supplies", "Pets", "Pet Carrier", "Pet Feeder",
        "Pet Fountain", "Pet Care Coops & Hutches", "Pet Care Farm Supplies",
        "Other Pet Supplies", "Bird Cages & Stands", "Aquarium", "Rabbit Cage"
    ],
    
    "fitness": [
        "Fitness", "Fitness Accessories", "Functional Fitness", "Weightlifting",
        "Dumbbells", "Kettlebells", "Gym Bench", "Exercise Bikes", "Treadmills",
        "Rowing Machine", "Boxing & Muay Thai", "MMA", "Martial Arts",
        "Gloves", "Focus Pads", "Thai Pads", "Body Protector", "Rashguard Shirts",
        "Air Track Mat", "Flooring & Mats", "Yoga Mat", "Trampoline",
        "Gym Sanitizer", "Basketball", "Rugby", "Golf"
    ],
    
    "office": [
        "Desks", "Desks Frame", "Chairs", "Filing Cabinets", "Office Cupboards",
        "Office Shelving", "Workstation", "Workstation Component", "Monitor Arm",
        "Pedestals", "Reception Counters", "Lectern", "Training Chairs",
        "Whiteboards", "Whiteboard", "Screens", "lockers", "Locker Stand", "Locker Top"
    ],
    
    "furniture": [
        "Bed", "Mattresses", "Sofa", "Lounge", "Recliners", "Ottoman",
        "Living Room Furniture", "Dining Room Furniture", "Bathroom Furniture",
        "Home Furniture", "Kids Furniture", "Bookcase", "Shelves", "Storage",
        "Tables", "Table Components", "Table & Chair Set", "Bar Stool", "Bench"
    ],
    
    "outdoor": [
        "Outdoor Furniture", "Home & Garden", "Vertical Garden",
        "Bikes", "Electric Scooters", "Electric Scooters Accessories"
    ],
    
    "electronics": [
        "CCTV Camera", "Speakers", "TV Acessories", "Projectors & Accessories",
        "Power Point", "Photography"
    ],
    
    "security": [
        "CCTV Camera", "Safety Lock", "lockers"
    ]
}

# =============================================================================
# CONTEXT KEYWORDS - What phrases suggest each category group
# =============================================================================

CONTEXT_KEYWORDS = {
    "pet": [
        "pet", "puppy", "dog", "cat", "kitten", "canine", "feline", "furry",
        "pooch", "pup", "doggy", "kitty", "bird", "fish", "aquarium", "rabbit",
        "bunny", "hamster", "guinea pig", "parrot", "chicken", "duck", "farm animal",
        "new pet", "pet owner", "pet parent", "fur baby", "adopted"
    ],
    
    "fitness": [
        "gym", "workout", "exercise", "fitness", "training", "muscle", "strength",
        "cardio", "weight", "lifting", "boxing", "mma", "martial arts", "kickboxing",
        "muay thai", "jiu jitsu", "karate", "yoga", "pilates", "crossfit",
        "home gym", "garage gym", "get fit", "lose weight", "build muscle",
        "bulk", "cut", "shred", "gains", "sweat", "athletic", "sport", "sports"
    ],
    
    "office": [
        "office", "work", "desk", "computer", "laptop", "working from home", "wfh",
        "remote work", "home office", "study", "workstation", "ergonomic",
        "productivity", "meeting", "conference", "reception", "business",
        "professional", "corporate", "back pain", "posture", "sit stand",
        "standing desk", "typing", "monitor", "screen"
    ],
    
    "furniture": [
        "furniture", "room", "bedroom", "living room", "dining", "bathroom",
        "home", "house", "apartment", "flat", "decor", "interior", "cozy",
        "comfortable", "relax", "sleep", "rest", "lounge", "sitting",
        "storage", "organize", "kid", "child", "children", "baby", "nursery"
    ],
    
    "outdoor": [
        "outdoor", "outside", "garden", "patio", "backyard", "balcony", "terrace",
        "deck", "lawn", "plants", "nature", "fresh air", "commute", "travel",
        "ride", "cycling", "scooter", "electric", "eco", "green"
    ],
    
    "electronics": [
        "camera", "security", "monitor", "screen", "tv", "television", "audio",
        "sound", "speaker", "projector", "presentation", "power", "electrical",
        "photo", "photography", "video", "recording"
    ]
}

# =============================================================================
# ITEM TO CATEGORY MAPPING - What specific items map to which categories
# =============================================================================

ITEM_CATEGORY_MAP = {
    # Pet items
    "collar": ["Dog Supplies", "Cat Supplies"],
    "leash": ["Dog Supplies"],
    "lead": ["Dog Supplies"],
    "harness": ["Dog Supplies", "Cat Supplies"],
    "pet bed": ["Dog Supplies", "Cat Supplies", "Pets"],
    "dog bed": ["Dog Supplies"],
    "cat bed": ["Cat Supplies"],
    "food bowl": ["Pet Feeder", "Dog Supplies", "Cat Supplies"],
    "water bowl": ["Pet Feeder", "Pet Fountain", "Dog Supplies", "Cat Supplies"],
    "water fountain": ["Pet Fountain"],
    "pet carrier": ["Pet Carrier"],
    "crate": ["Pet Carrier", "Dog Supplies"],
    "cage": ["Bird Cages & Stands", "Rabbit Cage"],
    "scratching post": ["Cat Supplies"],
    "litter": ["Cat Supplies"],
    "pet toy": ["Dog Supplies", "Cat Supplies"],
    "dog toy": ["Dog Supplies"],
    "cat toy": ["Cat Supplies"],
    "grooming": ["Dog Supplies", "Cat Supplies", "Pets"],
    "brush": ["Dog Supplies", "Cat Supplies"],
    "feeder": ["Pet Feeder"],
    "hutch": ["Pet Care Coops & Hutches"],
    "coop": ["Pet Care Coops & Hutches"],
    
    # Fitness items
    "dumbbell": ["Dumbbells", "Weightlifting"],
    "barbell": ["Weightlifting"],
    "kettlebell": ["Kettlebells"],
    "weight": ["Weightlifting", "Dumbbells", "Kettlebells"],
    "bench": ["Gym Bench", "Bench"],
    "treadmill": ["Treadmills"],
    "bike": ["Exercise Bikes", "Bikes"],
    "exercise bike": ["Exercise Bikes"],
    "rowing machine": ["Rowing Machine"],
    "rower": ["Rowing Machine"],
    "boxing gloves": ["Boxing & Muay Thai", "Gloves"],
    "gloves": ["Gloves", "Boxing & Muay Thai"],
    "punching bag": ["Boxing & Muay Thai"],
    "punch bag": ["Boxing & Muay Thai"],
    "focus pads": ["Focus Pads"],
    "thai pads": ["Thai Pads"],
    "yoga mat": ["Yoga Mat", "Flooring & Mats"],
    "mat": ["Flooring & Mats", "Yoga Mat", "Air Track Mat"],
    "trampoline": ["Trampoline"],
    "gym flooring": ["Flooring & Mats"],
    
    # Office items
    "desk": ["Desks", "Workstation"],
    "chair": ["Chairs", "Training Chairs"],
    "office chair": ["Chairs"],
    "monitor arm": ["Monitor Arm"],
    "monitor stand": ["Monitor Arm"],
    "filing cabinet": ["Filing Cabinets"],
    "cabinet": ["Filing Cabinets", "Office Cupboards"],
    "cupboard": ["Office Cupboards"],
    "shelf": ["Office Shelving", "Shelves"],
    "shelving": ["Office Shelving", "Shelves"],
    "locker": ["lockers"],
    "whiteboard": ["Whiteboards", "Whiteboard"],
    "screen": ["Screens"],
    "divider": ["Screens"],
    "pedestal": ["Pedestals"],
    "reception": ["Reception Counters"],
    "lectern": ["Lectern"],
    
    # Furniture items
    "bed": ["Bed"],
    "mattress": ["Mattresses"],
    "sofa": ["Sofa", "Lounge"],
    "couch": ["Sofa", "Lounge"],
    "recliner": ["Recliners"],
    "ottoman": ["Ottoman"],
    "bookcase": ["Bookcase"],
    "bookshelf": ["Bookcase", "Shelves"],
    "table": ["Tables", "Dining Room Furniture"],
    "dining table": ["Dining Room Furniture", "Tables"],
    "coffee table": ["Living Room Furniture", "Tables"],
    "bar stool": ["Bar Stool"],
    "stool": ["Bar Stool"],
    "kids table": ["Kids Furniture", "Table & Chair Set"],
    "kids chair": ["Kids Furniture", "Table & Chair Set"],
    "storage": ["Storage"],
    
    # Outdoor items
    "outdoor furniture": ["Outdoor Furniture"],
    "garden": ["Home & Garden", "Vertical Garden"],
    "patio": ["Outdoor Furniture"],
    "electric scooter": ["Electric Scooters"],
    "scooter": ["Electric Scooters"],
    "bicycle": ["Bikes"],
    
    # Electronics
    "camera": ["CCTV Camera", "Photography"],
    "cctv": ["CCTV Camera"],
    "security camera": ["CCTV Camera"],
    "speaker": ["Speakers"],
    "projector": ["Projectors & Accessories"],
    "power outlet": ["Power Point"],
    "power point": ["Power Point"],
}

# =============================================================================
# VAGUE PHRASE TRANSLATIONS - How to interpret vague/indirect queries
# =============================================================================

VAGUE_PHRASE_MAP = {
    # Pain/discomfort → ergonomic solutions
    "back hurts": {"categories": ["Chairs", "Desks"], "search_terms": ["ergonomic", "lumbar support"]},
    "back pain": {"categories": ["Chairs", "Desks"], "search_terms": ["ergonomic", "posture"]},
    "neck pain": {"categories": ["Chairs", "Monitor Arm"], "search_terms": ["ergonomic", "adjustable"]},
    "uncomfortable sitting": {"categories": ["Chairs"], "search_terms": ["ergonomic", "comfortable"]},
    "sitting all day": {"categories": ["Chairs", "Desks"], "search_terms": ["ergonomic", "sit stand"]},
    
    # Lifestyle → products
    "new puppy": {"categories": ["Dog Supplies", "Pet Feeder", "Pet Carrier"], "search_terms": ["puppy", "dog"]},
    "new dog": {"categories": ["Dog Supplies", "Pet Feeder", "Pet Carrier"], "search_terms": ["dog"]},
    "new kitten": {"categories": ["Cat Supplies", "Pet Feeder", "Pet Fountain"], "search_terms": ["cat", "kitten"]},
    "new cat": {"categories": ["Cat Supplies", "Pet Feeder", "Pet Fountain"], "search_terms": ["cat"]},
    "got a dog": {"categories": ["Dog Supplies", "Pet Feeder"], "search_terms": ["dog"]},
    "got a cat": {"categories": ["Cat Supplies", "Pet Feeder"], "search_terms": ["cat"]},
    "adopted a pet": {"categories": ["Dog Supplies", "Cat Supplies", "Pet Feeder"], "search_terms": ["pet"]},
    
    # Goals → products
    "lose weight": {"categories": ["Treadmills", "Exercise Bikes", "Fitness"], "search_terms": ["cardio"]},
    "get fit": {"categories": ["Fitness", "Dumbbells", "Exercise Bikes"], "search_terms": ["fitness"]},
    "build muscle": {"categories": ["Weightlifting", "Dumbbells", "Gym Bench"], "search_terms": ["weight", "strength"]},
    "home gym": {"categories": ["Fitness", "Dumbbells", "Gym Bench", "Flooring & Mats"], "search_terms": ["gym"]},
    "start boxing": {"categories": ["Boxing & Muay Thai", "Gloves", "Focus Pads"], "search_terms": ["boxing"]},
    "learn martial arts": {"categories": ["Martial Arts", "MMA", "Boxing & Muay Thai"], "search_terms": ["martial arts"]},
    "starting boxing": {"categories": ["Boxing & Muay Thai", "Gloves", "Focus Pads"], "search_terms": ["boxing"]},
    "want to box": {"categories": ["Boxing & Muay Thai", "Gloves", "Focus Pads"], "search_terms": ["boxing"]},
    "mma training": {"categories": ["MMA", "Boxing & Muay Thai", "Martial Arts"], "search_terms": ["mma"]},
    
    # Work situations
    "work from home": {"categories": ["Desks", "Chairs", "Monitor Arm"], "search_terms": ["office", "ergonomic"]},
    "home office": {"categories": ["Desks", "Chairs", "Filing Cabinets"], "search_terms": ["office"]},
    "remote work": {"categories": ["Desks", "Chairs", "Monitor Arm"], "search_terms": ["office", "desk"]},
    "study space": {"categories": ["Desks", "Chairs", "Bookcase"], "search_terms": ["desk", "study"]},
    
    # Pet acquisition variations
    "got a puppy": {"categories": ["Dog Supplies", "Pet Feeder", "Pet Carrier"], "search_terms": ["puppy", "dog"]},
    "just got a puppy": {"categories": ["Dog Supplies", "Pet Feeder", "Pet Carrier"], "search_terms": ["puppy", "dog"]},
    "got a dog": {"categories": ["Dog Supplies", "Pet Feeder", "Pet Carrier"], "search_terms": ["dog"]},
    "just got a dog": {"categories": ["Dog Supplies", "Pet Feeder", "Pet Carrier"], "search_terms": ["dog"]},
    "got a kitten": {"categories": ["Cat Supplies", "Pet Feeder", "Pet Fountain"], "search_terms": ["kitten", "cat"]},
    "just got a kitten": {"categories": ["Cat Supplies", "Pet Feeder", "Pet Fountain"], "search_terms": ["kitten", "cat"]},
    "have a dog": {"categories": ["Dog Supplies", "Pet Feeder"], "search_terms": ["dog"]},
    "have a cat": {"categories": ["Cat Supplies", "Pet Feeder"], "search_terms": ["cat"]},
    "have a puppy": {"categories": ["Dog Supplies", "Pet Feeder", "Pet Carrier"], "search_terms": ["puppy"]},
    "have a kitten": {"categories": ["Cat Supplies", "Pet Feeder", "Pet Fountain"], "search_terms": ["kitten"]},
    
    # Room setup
    "bedroom": {"categories": ["Bed", "Mattresses", "Bookcase"], "search_terms": ["bedroom"]},
    "living room": {"categories": ["Sofa", "Living Room Furniture", "Ottoman"], "search_terms": ["living room"]},
    "kids room": {"categories": ["Kids Furniture", "Bed", "Table & Chair Set"], "search_terms": ["kids"]},
}


class CategoryIntelligence:
    """
    Intelligent category mapping grounded in real catalog inventory.
    """
    
    def __init__(self):
        self.all_categories = set(ALL_CATEGORIES)
        self.category_groups = CATEGORY_GROUPS
        self.context_keywords = CONTEXT_KEYWORDS
        self.item_category_map = ITEM_CATEGORY_MAP
        self.vague_phrase_map = VAGUE_PHRASE_MAP
    
    def detect_context(self, text: str) -> Tuple[Optional[str], List[str]]:
        """
        Detect the context from text and return relevant categories.
        
        Returns:
            Tuple of (context_name, list_of_categories)
        """
        text_lower = text.lower()
        
        # Score each context by keyword matches
        context_scores = {}
        for context, keywords in self.context_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                context_scores[context] = score
        
        if not context_scores:
            return None, []
        
        # Get the highest scoring context
        best_context = max(context_scores, key=context_scores.get)
        categories = self.category_groups.get(best_context, [])
        
        return best_context, categories
    
    def get_categories_for_item(self, item: str) -> List[str]:
        """
        Get the relevant categories for a specific item.
        """
        item_lower = item.lower().strip()
        
        # Direct lookup
        if item_lower in self.item_category_map:
            return self.item_category_map[item_lower]
        
        # Partial match
        for key, categories in self.item_category_map.items():
            if key in item_lower or item_lower in key:
                return categories
        
        # Fallback: search in all categories for matching name
        matches = []
        for cat in self.all_categories:
            if item_lower in cat.lower() or cat.lower() in item_lower:
                matches.append(cat)
        
        return matches if matches else []
    
    def translate_vague_query(self, query: str) -> Dict:
        """
        Translate a vague/indirect query into search parameters.
        
        Returns:
            Dict with 'categories', 'search_terms', and 'detected_phrase'
        """
        query_lower = query.lower()
        
        # Check for known vague phrases
        for phrase, mapping in self.vague_phrase_map.items():
            if phrase in query_lower:
                return {
                    "detected_phrase": phrase,
                    "categories": mapping["categories"],
                    "search_terms": mapping["search_terms"],
                    "confidence": "high"
                }
        
        # Fallback to context detection
        context, categories = self.detect_context(query)
        if context:
            return {
                "detected_phrase": None,
                "context": context,
                "categories": categories,
                "search_terms": [],
                "confidence": "medium"
            }
        
        return {
            "detected_phrase": None,
            "categories": [],
            "search_terms": [],
            "confidence": "low"
        }
    
    def get_bundle_context(self, request: str) -> Dict:
        """
        Analyze a bundle request and return context-aware category filtering.
        
        Returns:
            Dict with 'bundle_context', 'allowed_categories', 'detected_items'
        """
        request_lower = request.lower()
        
        # Detect overall context
        context, base_categories = self.detect_context(request)
        
        # Extract specific items mentioned
        detected_items = []
        item_categories = set()
        
        for item, categories in self.item_category_map.items():
            if item in request_lower:
                detected_items.append(item)
                item_categories.update(categories)
        
        # Combine base categories with item-specific categories
        if context and base_categories:
            # Filter item categories to only those in the context group
            allowed = set(base_categories)
            if item_categories:
                # Add item-specific categories that are relevant
                allowed.update(item_categories & set(base_categories))
            allowed_categories = list(allowed)
        elif item_categories:
            allowed_categories = list(item_categories)
        else:
            allowed_categories = []
        
        return {
            "bundle_context": context,
            "allowed_categories": allowed_categories,
            "detected_items": detected_items,
            "base_group_categories": base_categories
        }
    
    def validate_category(self, category: str) -> bool:
        """Check if a category exists in the catalog."""
        return category in self.all_categories
    
    def find_similar_categories(self, query: str, limit: int = 5) -> List[str]:
        """Find categories that match the query."""
        query_lower = query.lower()
        
        matches = []
        for cat in self.all_categories:
            cat_lower = cat.lower()
            if query_lower in cat_lower or cat_lower in query_lower:
                matches.append(cat)
        
        # Also check context keywords
        if not matches:
            context, categories = self.detect_context(query)
            if categories:
                matches = categories[:limit]
        
        return matches[:limit]


# Singleton instance
_category_intelligence = None

def get_category_intelligence() -> CategoryIntelligence:
    """Get the singleton CategoryIntelligence instance."""
    global _category_intelligence
    if _category_intelligence is None:
        _category_intelligence = CategoryIntelligence()
    return _category_intelligence
