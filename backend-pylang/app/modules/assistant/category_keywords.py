"""
Comprehensive list of all product categories and their variations.
Used for intent detection to recognize product searches immediately.
"""

# All categories from your catalog with singular/plural forms and common variations
ALL_CATEGORY_KEYWORDS = {
    # Furniture
    "recliner", "recliners", "recliner chair", "reclining chair",
    "sofa", "sofas", "couch", "couches", "lounge", "lounges",
    "chair", "chairs", "seating", "seat", "seats",
    "desk", "desks", "office desk", "computer desk", "standing desk",
    "desk frame", "desk frames", "desks frame",
    "table", "tables", "dining table", "coffee table",
    "bed", "beds", "bed frame", "bed frames", "bedframe", "bedframes",
    "mattress", "mattresses",
    "bench", "benches",
    "ottoman", "ottomans",
    "bookcase", "bookcases", "bookshelf", "bookshelves",
    "shelves", "shelf", "shelving",
    "cabinet", "cabinets", "cupboard", "cupboards",
    "locker", "lockers", "locker stand", "locker top",
    "storage", "storage unit", "storage units",
    "workstation", "workstations", "work station",
    "workstation component", "workstation components",
    "pedestals", "pedestal",
    "mirror", "mirrors",
    
    # Office Furniture
    "office chair", "office chairs", "ergonomic chair", "ergonomic chairs",
    "office furniture", "office cupboard", "office cupboards",
    "office shelving", "filing cabinet", "filing cabinets",
    "reception counter", "reception counters", "reception desk",
    "lectern", "lecterns", "podium",
    "whiteboard", "whiteboards", "white board",
    "monitor arm", "monitor arms", "monitor stand",
    "training chair", "training chairs",
    
    # Living Room
    "living room furniture", "living room",
    "bar stool", "bar stools", "barstool", "barstools",
    "dining room furniture", "dining furniture",
    "home furniture", "home decor",
    "kids furniture", "children furniture",
    "bathroom furniture", "bathroom",
    
    # Outdoor
    "outdoor furniture", "outdoor", "patio furniture", "garden furniture",
    "vertical garden", "garden", "home garden", "home & garden",
    
    # Tables
    "table components", "table component",
    "table chair set", "table and chair", "dining set",
    
    # Pet Supplies - Dogs
    "dog", "dogs", "dog supplies", "dog supply", "puppy", "puppies",
    "dog bed", "dog beds", "dog bowl", "dog bowls",
    "dog toy", "dog toys", "dog collar", "dog leash",
    "dog crate", "dog cage", "dog kennel",
    "dog food", "dog treat", "dog treats",
    
    # Pet Supplies - Cats
    "cat", "cats", "cat supplies", "cat supply", "kitten", "kittens",
    "cat bed", "cat beds", "cat bowl", "cat bowls",
    "cat toy", "cat toys", "cat tree", "cat tower",
    "cat scratching post", "scratching post", "cat scratcher",
    "cat litter", "litter box", "cat food",
    
    # Pet Supplies - Birds
    "bird", "birds", "bird cage", "bird cages", "birdcage", "birdcages",
    "bird stand", "bird stands", "bird perch",
    "parrot", "parrots", "parrot cage", "aviary",
    "bird feeder", "bird feeders",
    
    # Pet Supplies - Fish
    "aquarium", "aquariums", "fish tank", "fish tanks", "fishtank",
    "fish", "fishes", "fish bowl", "fish bowls",
    "aquarium accessories", "fish accessories",
    
    # Pet Supplies - Small Animals
    "rabbit", "rabbits", "rabbit cage", "rabbit hutch", "bunny",
    "hamster", "hamster cage", "guinea pig",
    "pet carrier", "pet carriers", "pet cage",
    "pet feeder", "pet feeders", "pet fountain", "pet fountains",
    "pet care", "pet supplies", "pet products", "pets",
    "pet care coops", "pet hutches", "coops", "hutches",
    "pet care farm", "farm supplies",
    
    # Other Pet
    "other pet supplies", "small animal", "small animals",
    
    # Fitness - General
    "fitness", "fitness equipment", "gym", "gym equipment",
    "exercise", "workout", "training",
    "fitness accessories", "gym accessories",
    
    # Fitness - Cardio
    "treadmill", "treadmills", "running machine",
    "exercise bike", "exercise bikes", "stationary bike", "spin bike",
    "rowing machine", "rowing machines", "rower",
    "trampoline", "trampolines",
    
    # Fitness - Strength
    "dumbbell", "dumbbells", "dumb bell", "dumb bells",
    "kettlebell", "kettlebells", "kettle bell",
    "weightlifting", "weight lifting", "weights", "weight",
    "gym bench", "gym benches", "weight bench",
    "functional fitness", "crossfit",
    
    # Fitness - Mats & Flooring
    "yoga mat", "yoga mats", "yoga", "exercise mat",
    "air track mat", "air track", "airtrack",
    "flooring", "gym flooring", "mats", "mat", "floor mat",
    "gym sanitizer",
    
    # Boxing & Martial Arts
    "boxing", "muay thai", "boxing equipment", "boxing gloves",
    "mma", "mixed martial arts", "ufc",
    "martial arts", "karate", "judo", "jiu jitsu",
    "punching bag", "punch bag", "heavy bag",
    "focus pads", "focus pad", "mitts",
    "thai pads", "thai pad", "kick pads",
    "body protector", "chest guard",
    "gloves", "glove", "boxing glove",
    "rashguard", "rashguard shirts", "rash guard",
    
    # Sports
    "basketball", "basketball hoop", "basketball equipment",
    "rugby", "rugby ball", "rugby equipment",
    "golf", "golf equipment", "golf accessories",
    "bikes", "bike", "bicycle", "bicycles", "cycling",
    
    # Electric Scooters
    "electric scooter", "electric scooters", "e-scooter", "escooter",
    "scooter", "scooters", "e scooter",
    "electric scooter accessories", "scooter accessories",
    
    # Electronics & Tech
    "cctv", "cctv camera", "cctv cameras", "security camera",
    "camera", "cameras", "surveillance",
    "power point", "power points", "powerpoint", "power outlet",
    "projector", "projectors", "projector accessories",
    "speaker", "speakers", "audio",
    "screen", "screens", "display", "tv",
    "tv accessories", "television",
    "photography", "photo equipment", "lighting",
    
    # Accessories & Misc
    "accessories", "accessory",
    "trolley", "trolleys", "cart",
    "safety lock", "safety locks", "lock", "locks",
    "snughooks", "hooks",
    "general",
}

# Create lowercase set for fast lookup
ALL_CATEGORY_KEYWORDS_LOWER = {kw.lower() for kw in ALL_CATEGORY_KEYWORDS}

def _fuzzy_match(word: str, keyword: str, max_distance: int = 1) -> bool:
    """
    Simple fuzzy match: checks if word is similar to keyword with at most max_distance edits.
    Handles common typos like 'reclineer' -> 'recliner', 'aqurium' -> 'aquarium'
    """
    if len(word) < 3 or len(keyword) < 3:
        return word == keyword
    
    # Must be within 2 chars of length
    if abs(len(word) - len(keyword)) > 2:
        return False
    
    # Check prefix match (first 3+ chars)
    min_prefix = min(3, min(len(word), len(keyword)))
    if word[:min_prefix] != keyword[:min_prefix]:
        return False
    
    # Count character differences
    differences = 0
    longer = max(word, keyword, key=len)
    shorter = min(word, keyword, key=len)
    
    j = 0
    for i, c in enumerate(longer):
        if j < len(shorter) and c == shorter[j]:
            j += 1
        else:
            differences += 1
            if differences > max_distance:
                return False
    
    return True

def is_product_search_term(message: str) -> bool:
    """
    Check if message contains any known product/category term.
    Returns True if it's likely a product search.
    Includes fuzzy matching for typos.
    """
    message_lower = message.lower().strip()
    
    # Direct match
    if message_lower in ALL_CATEGORY_KEYWORDS_LOWER:
        return True
    
    # Check if any keyword is in the message
    message_words = set(message_lower.split())
    for keyword in ALL_CATEGORY_KEYWORDS_LOWER:
        # Single word keyword match
        if keyword in message_words:
            return True
        # Multi-word keyword match
        if " " in keyword and keyword in message_lower:
            return True
    
    # Fuzzy match for typos (single word messages)
    if len(message_words) <= 2:
        for word in message_words:
            if len(word) >= 4:  # Only fuzzy match longer words
                for keyword in ALL_CATEGORY_KEYWORDS_LOWER:
                    if " " not in keyword and _fuzzy_match(word, keyword):
                        return True
    
    return False

def get_matching_category(message: str) -> str | None:
    """
    Get the matching category keyword from a message.
    Returns the matched keyword or None.
    """
    message_lower = message.lower().strip()
    
    # Direct match first
    if message_lower in ALL_CATEGORY_KEYWORDS_LOWER:
        return message_lower
    
    # Check multi-word keywords first (more specific)
    for keyword in sorted(ALL_CATEGORY_KEYWORDS_LOWER, key=len, reverse=True):
        if " " in keyword and keyword in message_lower:
            return keyword
    
    # Then check single words
    message_words = set(message_lower.split())
    for keyword in ALL_CATEGORY_KEYWORDS_LOWER:
        if keyword in message_words:
            return keyword
    
    return None
