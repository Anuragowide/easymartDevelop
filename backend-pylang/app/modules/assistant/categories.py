"""
Product Category Mapping for EasyMart
This module contains all product categories and subcategories used across the platform.
"""

from typing import Dict, List, Optional

# Main categories with their subcategories
CATEGORY_MAPPING: Dict[str, List[str]] = {
    "Sports & Fitness": [
        # Fitness Accessories
        "Fitness Accessories",
        "Treadmills",
        "Exercise Bikes",
        "Rowing Machines",
        "Dumbbells",
        "Kettlebell",
        "Gym Bench",
        "Air Track Mat",
        "Trampolines",
        "Bench & Gym Equipment",
        
        # Boxing & Muay Thai
        "Boxing & Muay Thai",
        "Apparel, Shoes & Carry Bags",
        "Boxing Bags & Training Accessories",
        "Protective Equipment",
        "Boxing Rings & Accessories",
        "Focus Pads & Kick Shields",
        
        # Martial Arts
        "Martial Arts",
        "Martial Arts Uniforms & Belts",
        "Martial Arts Training Weapons",
        "Martial Arts Protective Equipment",
        "Martial Arts Punch Kick Hit Shields",
        "Martial Arts Shoes & Gear Bags",
        
        # Functional Fitness
        "Functional Fitness",
        "Strength Equipment",
        "Conditioning Equipment",
        "Speed And Agility Equipment",
        "Body Weight Equipment",
        "Mobility And Recovery Equipment",
        
        # Weightlifting
        "Weightlifting",
        "Barbells, Barbell Storage & Accessories",
        "Olympic Weight Plates and Sets",
        
        # Other Sports
        "MMA",
        "Rugby",
        "Basketball and Accessories",
    ],
    
    "Electric Scooters": [
        "Electric Scooters",
        "Scooters Accessories",
    ],
    
    "Office Furniture": [
        # Desks
        "Desks",
        "Computer Desks",
        "Corner Desks",
        "Sit Stand Desks",
        "L Shaped Desk",
        "Office Desk",
        "Study Desks",
        "Workstations",
        "Drawing Desks",
        "Reception Desk",
        "Desk Frame",
        
        # Chairs
        "Chairs",
        "Gaming Chairs",
        "Executive Chair",
        "Desk Chair",
        "Mesh Office Chair",
        "Ergonomic Chairs",
        "Computer Chairs",
        "Swivel Chair",
        "Massage Chairs",
        "Visitor Chairs",
        
        # Tables
        "Tables",
        "Boardroom Tables",
        "Meeting Tables",
        "Coffee Tables",
        "Round Tables",
        "Folding Tables",
        "Bar Tables",
        "General Purpose Tables",
        "Table Frame & Accessories",
        
        # Filing & Storage
        "Filing & Storage",
        "Office Cupboards",
        "Bookcases & Bookshelves",
        "Filing Cabinets",
        "Pedestal Drawer Units",
        "Office Shelving",
        "Storage Cabinets",
        "Credenza & Sliding Door Sideboards",
        
        # Office Accessories
        "Office Accessories",
        "Power Points",
        "Monitor Arms",
        "Modular Wiring",
        "Desk Screens and Accessories",
        "Vertical Garden",
        "Safety & Hooks",
        "Office Pods",
    ],
    
    "Hospitality Furniture": [
        # By Type
        "Bar Stools",
        "Bar Tables",
        "Coffee Tables",
        "Cafe Chairs",
        "Cafe Tables",
        "Sofas",
        
        # By Place
        "Bar Furniture",
        "Lounge Furniture",
        "Outdoor Furniture",
        "Cafe Furniture",
        "Garden Furniture",
        "Reception Seating",
    ],
    
    "Home Furniture": [
        # By Type
        "Bedside Tables",
        "Shoe Storage Cabinets",
        "Mattresses",
        "Entertainment TV Units",
        "Bar Stools",
        "Ottomans",
        
        # By Place
        "Bedroom Furniture",
        "Living Room Furniture",
        "Dining Room Furniture",
        "Kids Room Furniture",
        "Bathroom Furniture",
        "Garden Furniture",
        "Outdoor Furniture",
    ],
    
    "Pet Products": [
        # Dog Products
        "Dog Products",
        "Dogs Kennel",
        "Dog Pram",
        "Dog Toys",
        "Dog Cage",
        "Dogs Training Pads",
        "Dog Bowls and Dispensers",
        "Dog Car Seat Covers",
        "Dog Collars and Leads",
        
        # Cat Products
        "Cats Products",
        "Cat Tree",
        "Cat Litter Box",
        "Cats Bedding",
        "Cat Carrier",
        "Cat Toys",
        "Cat Bowls & Food Dispensers",
        
        # Other Products
        "Other Products",
        "Bird Cages & Aviaries",
        "Pet Farm Supplies",
        "Pet Coops & Hutches",
        "Aquarium Pumps & Filters",
    ],
}

# Flat list of all categories for quick lookup
ALL_CATEGORIES: List[str] = list(CATEGORY_MAPPING.keys())

# Flat list of all subcategories
ALL_SUBCATEGORIES: List[str] = [
    subcategory 
    for subcategories in CATEGORY_MAPPING.values() 
    for subcategory in subcategories
]

# Combined list for search matching
ADAPTER_CATEGORIES: List[str] = [
    "Accessories",
    "Air Track Mat",
    "Aquarium",
    "Bar Stool",
    "Basketball",
    "Bathroom Furniture",
    "Bed",
    "Bench",
    "Bikes",
    "Bird Cages & Stands",
    "Body Protector",
    "Bookcase",
    "Boxing & Muay Thai",
    "CCTV Camera",
    "Cat Supplies",
    "Chairs",
    "Desks",
    "Desks Frame",
    "Dining Room Furniture",
    "Dog Supplies",
    "Dumbbells",
    "Electric Scooters",
    "Electric Scooters Accessories",
    "Exercise Bikes",
    "Filing Cabinets",
    "Fitness",
    "Fitness Accessories",
    "Flooring & Mats",
    "Focus Pads",
    "Functional Fitness",
    "General",
    "Gloves",
    "Golf",
    "Gym Bench",
    "Gym Sanitizer",
    "Home & Garden",
    "Home Furniture",
    "Kettlebells",
    "Kids Furniture",
    "Lectern",
    "Living Room Furniture",
    "Locker Stand",
    "Locker Top",
    "Lounge",
    "MMA",
    "Martial Arts",
    "Mattresses",
    "Mirror",
    "Monitor Arm",
    "Office Cupboards",
    "Office Shelving",
    "Other Pet Supplies",
    "Ottoman",
    "Outdoor Furniture",
    "Pedestals",
    "Pet Care Coops & Hutches",
    "Pet Care Farm Supplies",
    "Pet Carrier",
    "Pet Feeder",
    "Pet Fountain",
    "Pets",
    "Photography",
    "Power Point",
    "Projectors & Accessories",
    "Rabbit Cage",
    "Rashguard Shirts",
    "Reception Counters",
    "Recliners",
    "Rowing Machine",
    "Rugby",
    "Safety Lock",
    "Screens",
    "Shelves",
    "Snughooks",
    "Sofa",
    "Speakers",
    "Storage",
    "TV Acessories",
    "Table & Chair Set",
    "Table Components",
    "Tables",
    "Thai Pads",
    "Training Chairs",
    "Trampoline",
    "Treadmills",
    "Trolley",
    "Vertical Garden",
    "Weightlifting",
    "Whiteboard",
    "Whiteboards",
    "Workstation",
    "Workstation Component",
    "Yoga Mat",
    "lockers",
]

ALL_PRODUCT_TYPES: List[str] = ALL_CATEGORIES + ALL_SUBCATEGORIES + ADAPTER_CATEGORIES

# Category aliases for better search matching
CATEGORY_ALIASES: Dict[str, List[str]] = {
    "Sports & Fitness": ["sports", "fitness", "gym", "exercise", "workout", "training"],
    "Electric Scooters": ["scooter", "escooter", "e-scooter", "electric scooter"],
    "Office Furniture": ["office", "desk", "chair", "workspace", "work furniture"],
    "Hospitality Furniture": ["hospitality", "hotel", "restaurant", "cafe", "commercial"],
    "Home Furniture": ["home", "house", "residential", "living", "bedroom"],
    "Pet Products": ["pet", "dog", "cat", "bird", "animal", "pet supplies"],
}

# Subcategory aliases for better matching
SUBCATEGORY_ALIASES: Dict[str, List[str]] = {
    # Fitness Equipment
    "Dumbbells": ["dumbbell", "weights", "free weights", "hand weights"],
    "Treadmills": ["treadmill", "running machine", "cardio", "runner"],
    "Exercise Bikes": ["bike", "cycling", "stationary bike", "spin bike", "cycle", "exercise bike"],
    "Kettlebell": ["kettlebell", "kettle bell", "kettlebells"],
    "Rowing Machines": ["rowing machine", "rower", "rowing"],
    "Bench & Gym Equipment": ["gym bench", "weight bench", "workout bench"],
    
    # Boxing & Muay Thai
    "Boxing & Muay Thai": ["boxing", "muay thai", "boxing equipment", "boxing gear", "muay thai gear"],
    "Boxing Bags & Training Accessories": ["punching bag", "heavy bag", "boxing bag", "speed bag", "punch bag", "training bag"],
    "Protective Equipment": ["protective gear", "protection", "boxing gloves", "mma gloves", "sparring gloves", "training gloves", "leather gloves", "headgear", "shin guards", "mouth guard", "groin protector"],
    "Focus Pads & Kick Shields": ["focus pads", "kick shield", "thai pads", "strike shield", "training pad", "mitt", "mitts"],
    "Boxing Rings & Accessories": ["boxing ring", "ring", "ring accessories"],
    
    # Martial Arts
    "Martial Arts": ["martial arts", "karate", "taekwondo", "judo", "jiu jitsu", "bjj"],
    "Martial Arts Uniforms & Belts": ["gi", "uniform", "karate uniform", "belt", "martial arts uniform", "karate gi"],
    "Martial Arts Training Weapons": ["training weapon", "wooden sword", "bo staff", "nunchaku", "training sword"],
    "Martial Arts Protective Equipment": ["martial arts gear", "protective equipment", "sparring gear"],
    
    # MMA & Combat Sports
    "MMA": ["mma", "mixed martial arts", "mma equipment", "mma gear", "fight gear", "ufc", "cage fighting"],
    "Rugby": ["rugby", "rugby ball", "rugby equipment"],
    "Basketball and Accessories": ["basketball", "basketball hoop", "basketball ring"],
    
    # Weightlifting
    "Weightlifting": ["weightlifting", "powerlifting", "olympic lifting", "weight training"],
    "Barbells, Barbell Storage & Accessories": ["barbell", "olympic bar", "weight bar", "barbell rack", "bar"],
    "Olympic Weight Plates and Sets": ["weight plates", "olympic plates", "bumper plates", "iron plates", "plates"],
    
    # Furniture
    "Gaming Chairs": ["gaming chair", "gamer chair", "esports chair", "gaming seat"],
    "Sit Stand Desks": ["standing desk", "height adjustable", "sit-stand", "adjustable desk"],
    
    # Pet Products
    "Dogs Kennel": ["dog house", "kennel", "dog shelter", "dog home", "dog crate"],
    "Cat Tree": ["cat tower", "cat climber", "scratching post", "cat furniture"],
    
    # Electric Scooters
    "Electric Scooters": ["e-scooter", "electric scooter", "scooter"],
}


def get_category_for_subcategory(subcategory: str) -> Optional[str]:
    """Get the main category for a given subcategory"""
    for category, subcategories in CATEGORY_MAPPING.items():
        if subcategory in subcategories:
            return category
    return None


def is_valid_category(category: str) -> bool:
    """Check if a category is valid"""
    return category in ALL_CATEGORIES or category in ALL_SUBCATEGORIES or category in ADAPTER_CATEGORIES


def is_valid_subcategory(subcategory: str) -> bool:
    """Check if a subcategory is valid"""
    return subcategory in ALL_SUBCATEGORIES


def get_subcategories(category: str) -> List[str]:
    """Get all subcategories for a given category"""
    return CATEGORY_MAPPING.get(category, [])


def match_category_from_query(query: str) -> Optional[str]:
    """
    Match a category from a user query using aliases
    Returns the main category name if found, None otherwise
    """
    query_lower = query.lower()
    
    # Check direct category match
    for category in ALL_CATEGORIES:
        if category.lower() in query_lower:
            return category
    
    # Check category aliases
    for category, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            if alias.lower() in query_lower:
                return category
    
    return None


def match_subcategory_from_query(query: str) -> Optional[str]:
    """
    Match a subcategory from a user query using aliases
    Returns the subcategory name if found, None otherwise
    """
    query_lower = query.lower()
    
    # Check direct subcategory match
    for subcategory in ALL_SUBCATEGORIES:
        if subcategory.lower() in query_lower:
            return subcategory
    
    # Check subcategory aliases
    for subcategory, aliases in SUBCATEGORY_ALIASES.items():
        for alias in aliases:
            if alias.lower() in query_lower:
                return subcategory

    for category in ADAPTER_CATEGORIES:
        if category.lower() in query_lower:
            return category

    return None


def get_category_summary() -> str:
    """Get a formatted summary of all categories and their subcategory counts"""
    summary = []
    for category, subcategories in CATEGORY_MAPPING.items():
        summary.append(f"{category}: {len(subcategories)} subcategories")
    return "\n".join(summary)
